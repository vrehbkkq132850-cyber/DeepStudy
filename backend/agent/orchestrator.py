"""
Agent 编排器
使用 LlamaIndex 编排对话流程
"""
import uuid
import logging
import json
from typing import Optional
from backend.agent.llm_client import ModelScopeLLMClient
from backend.agent.intent_router import IntentRouter, IntentType
from backend.agent.strategies import DerivationStrategy, CodeStrategy, ConceptStrategy
from backend.agent.prompts.system_prompts import RECURSIVE_PROMPT, KNOWLEDGE_EXTRACTION_PROMPT
from backend.api.schemas.response import AgentResponse
from backend.data.neo4j_client import neo4j_client
from backend.config import settings

# 配置日志
logger = logging.getLogger(__name__)


class AgentOrchestrator:
    """
    Agent 编排器
    负责协调意图识别、策略选择和响应生成
    """
    
    def __init__(self):
        """初始化编排器"""
        logger.info("开始初始化 Orchestrator...")
        
        logger.info(f"初始化主模型: {settings.MODEL_NAME}")
        # 使用 OpenAI 兼容 API
        self.llm = ModelScopeLLMClient(
            model_name=settings.MODEL_NAME,
            api_key=settings.MODELSCOPE_API_KEY,
            api_base=settings.MODELSCOPE_API_BASE
        )
        logger.info("主模型初始化成功")
        
        logger.info(f"初始化 Coder 模型: {settings.CODER_MODEL_NAME}")
        self.coder_llm = ModelScopeLLMClient(
            model_name=settings.CODER_MODEL_NAME,
            api_key=settings.MODELSCOPE_API_KEY,
            api_base=settings.MODELSCOPE_API_BASE
        )
        logger.info("Coder 模型初始化成功")
        
        # 初始化意图路由器
        logger.info("初始化意图路由器...")
        self.intent_router = IntentRouter(self.llm)
        
        # 初始化策略
        logger.info("初始化策略...")
        self.strategies = {
            IntentType.DERIVATION: DerivationStrategy(self.llm),
            IntentType.CODE: CodeStrategy(self.coder_llm),
            IntentType.CONCEPT: ConceptStrategy(self.llm),
        }
        logger.info("Orchestrator 初始化完成")
    
    async def extract_knowledge_triples(self, query: str, answer: str, conversation_id: str, user_id: str) -> list:
        """
        提取知识三元组并保存到Neo4j
        
        Args:
            query: 用户问题
            answer: AI回答
            conversation_id: 对话ID
            user_id: 用户ID
            
        Returns:
            知识三元组列表
        """
        try:
            # 构建知识提取提示词
            prompt = KNOWLEDGE_EXTRACTION_PROMPT.format(query=query, answer=answer)
            
            # 调用LLM提取知识三元组
            logger.info("开始提取知识三元组...")
            response_text = await self.llm.acomplete(prompt)
            response_content = response_text.text if hasattr(response_text, 'text') else str(response_text)
            
            # 解析JSON响应
            try:
                # 尝试提取JSON部分
                json_start = response_content.find('[')
                json_end = response_content.rfind(']') + 1
                if json_start >= 0 and json_end > json_start:
                    json_str = response_content[json_start:json_end]
                    knowledge_triples = json.loads(json_str)
                else:
                    knowledge_triples = json.loads(response_content)
                
                logger.info(f"成功提取 {len(knowledge_triples)} 个知识三元组")
                
                # 保存知识三元组到Neo4j
                for triple in knowledge_triples:
                    subject = triple.get("subject", "")
                    relation = triple.get("relation", "")
                    obj = triple.get("object", "")
                    
                    if subject and relation and obj:
                        await neo4j_client.save_knowledge_triple(
                            subject=subject,
                            relation=relation,
                            obj=obj,
                            user_id=user_id,
                            conversation_id=conversation_id
                        )
                        logger.info(f"保存知识三元组: {subject} -> {relation} -> {obj}")
                
                return knowledge_triples
            except json.JSONDecodeError as e:
                logger.error(f"解析知识三元组JSON失败: {e}, 响应内容: {response_content}")
                return []
        except Exception as e:
            logger.error(f"提取知识三元组失败: {str(e)}", exc_info=True)
            return []
    
    async def process_query(
        self,
        user_id: str,
        query: str,
        parent_id: Optional[str] = None,
        session_id: Optional[str] = None
    ) -> AgentResponse:
        """
        处理用户查询
        
        Args:
            user_id: 用户 ID
            query: 用户查询
            parent_id: 父对话 ID（可选）
            
        Returns:
            Agent 响应
        """
        logger.info(f"开始处理查询: query={query[:50]}...")
        # 识别意图
        logger.info("识别意图...")
        intent = await self.intent_router.route(query)
        logger.info(f"识别结果: {intent.value}")
        
        # 选择策略
        logger.info(f"选择策略: {intent.value}")
        strategy = self.strategies[intent]
        
        # 处理查询
        logger.info("调用策略处理查询...")
        context = {
            "user_id": user_id,
            "parent_id": parent_id,
        }
        response = await strategy.process(query, context)
        logger.info("策略处理完成")
        
        # 生成对话 ID
        conversation_id = str(uuid.uuid4())
        response.conversation_id = conversation_id
        response.parent_id = parent_id
        logger.info(f"生成对话 ID: {conversation_id}")
        
        # 保存到 Neo4j
        logger.info("开始保存到 Neo4j...")
        try:
            # 创建用户节点
            user_node_id = f"{conversation_id}_user"
            await neo4j_client.save_dialogue_node(
                node_id=user_node_id,
                user_id=user_id,
                role="user",
                content=query,
                intent=intent.value if intent else None
            )
            
            # 创建 AI 节点
            ai_node_id = conversation_id
            await neo4j_client.save_dialogue_node(
                node_id=ai_node_id,
                user_id=user_id,
                role="assistant",
                content=response.answer,
                intent=intent.value if intent else None
            )
            
            # 创建用户到 AI 的关系
            await neo4j_client.link_dialogue_nodes(
                parent_node_id=user_node_id,
                child_node_id=ai_node_id
            )
            
            # 如果有父节点，创建父节点到用户节点的关系
            if parent_id:
                logger.info(f"创建父节点关系: parent_id={parent_id}")
                # 父节点应该是 AI 节点（conversation_id）
                await neo4j_client.link_dialogue_nodes(
                    parent_node_id=parent_id,
                    child_node_id=user_node_id
                )
            logger.info("Neo4j 保存成功")
        except Exception as e:
            logger.error(f"保存对话到 Neo4j 失败: {str(e)}", exc_info=True)
            # 严格模式：Neo4j 失败则整个请求失败
            raise RuntimeError(f"保存对话到 Neo4j 失败: {str(e)}") from e
        
        # 提取知识三元组并保存到Neo4j
        logger.info("开始提取知识三元组...")
        knowledge_triples = await self.extract_knowledge_triples(
            query=query,
            answer=response.answer,
            conversation_id=conversation_id,
            user_id=user_id
        )
        response.knowledge_triples = knowledge_triples
        logger.info(f"知识三元组提取完成，共 {len(knowledge_triples)} 个")
        
        return response
    
    async def process_recursive_query(
        self,
        user_id: str,
        parent_id: str,
        fragment_id: str,
        query: str
    ) -> AgentResponse:
        """
        处理递归追问
        
        Args:
            user_id: 用户 ID
            parent_id: 父对话 ID
            fragment_id: 选中的文本片段 ID
            query: 追问内容
            
        Returns:
            Agent 响应
        """
              
        # 使用递归提示词
        prompt = f"{RECURSIVE_PROMPT}\n\n用户追问: {query}\n\n请针对性地回答："
        
        response_text = await self.llm.acomplete(prompt)
        answer = response_text.text if hasattr(response_text, 'text') else str(response_text)
        
        return AgentResponse(
            answer=answer,
            fragments=[],
            knowledge_triples=[],
            conversation_id=str(uuid.uuid4()),
            parent_id=parent_id
        )
