"""
Agent 编排器
使用 LlamaIndex 编排对话流程
集成：IntentRouter (意图识别) + VectorStore (RAG检索) + Neo4j (知识存储)
"""
import uuid
import logging
import json
from typing import Optional

# --- 核心组件 ---
from backend.agent.llm_client import ModelScopeLLMClient
from backend.agent.intent_router import IntentRouter, IntentType
from backend.agent.strategies import DerivationStrategy, CodeStrategy, ConceptStrategy
from backend.agent.prompts.system_prompts import RECURSIVE_PROMPT, KNOWLEDGE_EXTRACTION_PROMPT
from backend.api.schemas.response import AgentResponse
from backend.data.neo4j_client import neo4j_client
from backend.config import settings

# --- 新增：引入你的向量库管理器 ---
from backend.data.vector_store import vector_store_manager

# 配置日志
logger = logging.getLogger(__name__)


class AgentOrchestrator:
    """
    Agent 编排器
    负责协调意图识别、RAG检索、策略选择和响应生成
    """
    
    def __init__(self):
        """初始化编排器"""
        logger.info("🚀 [Orchestrator] 开始初始化...")
        
        logger.info(f"Step 1: 初始化主模型: {settings.MODEL_NAME}")
        self.llm = ModelScopeLLMClient(
            model_name=settings.MODEL_NAME,
            api_key=settings.MODELSCOPE_API_KEY,
            api_base=settings.MODELSCOPE_API_BASE
        )
        
        logger.info(f"Step 2: 初始化 Coder 模型: {settings.CODER_MODEL_NAME}")
        self.coder_llm = ModelScopeLLMClient(
            model_name=settings.CODER_MODEL_NAME,
            api_key=settings.MODELSCOPE_API_KEY,
            api_base=settings.MODELSCOPE_API_BASE
        )
        
        # 初始化意图路由器
        logger.info("Step 3: 初始化意图路由器...")
        self.intent_router = IntentRouter(self.llm)
        
        # 初始化策略
        logger.info("Step 4: 初始化处理策略...")
        self.strategies = {
            IntentType.DERIVATION: DerivationStrategy(self.llm),
            IntentType.CODE: CodeStrategy(self.coder_llm),
            IntentType.CONCEPT: ConceptStrategy(self.llm),
        }
        logger.info("[Orchestrator] 初始化完成")
    
    async def extract_knowledge_triples(self, query: str, answer: str, conversation_id: str, user_id: str) -> list:
        """
        提取知识三元组并保存到Neo4j (保持不变)
        """
        try:
            prompt = KNOWLEDGE_EXTRACTION_PROMPT.format(query=query, answer=answer)
            logger.info("[Knowledge] 开始提取知识三元组...")
            response_text = await self.llm.acomplete(prompt)
            response_content = response_text.text if hasattr(response_text, 'text') else str(response_text)
            
            try:
                json_start = response_content.find('[')
                json_end = response_content.rfind(']') + 1
                if json_start >= 0 and json_end > json_start:
                    json_str = response_content[json_start:json_end]
                    knowledge_triples = json.loads(json_str)
                else:
                    knowledge_triples = json.loads(response_content)
                
                logger.info(f"[Knowledge] 成功提取 {len(knowledge_triples)} 个三元组")
                
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
                return knowledge_triples
            except json.JSONDecodeError:
                logger.warning(f"[Knowledge] JSON解析失败，跳过三元组提取")
                return []
        except Exception as e:
            logger.error(f"[Knowledge] 提取失败: {str(e)}")
            return []
    
    async def process_query(
        self,
        user_id: str,
        query: str,
        parent_id: Optional[str] = None,
        session_id: Optional[str] = None
    ) -> AgentResponse:
        """
        处理用户查询 (核心逻辑修改点)
        流程：意图识别 -> RAG检索 -> 策略执行 -> 存入Neo4j
        """
        logger.info(f"🤖 [Process] 收到用户查询: {query[:50]}...")
        
        # 1. 识别意图
        intent = await self.intent_router.route(query)
        logger.info(f" [Intent] 识别结果: {intent.value}")
        
        # =====================================================
        #  核心修改：在这里加入 RAG 检索逻辑 
        # =====================================================
        logger.info("[RAG] 正在检索本地向量知识库...")
        try:
            # 调用你写的 vector_store
            rag_results = await vector_store_manager.search_context(query, top_k=3)
            
            rag_context_str = ""
            if rag_results:
                logger.info(f"[RAG] 命中 {len(rag_results)} 条相关资料")
                # 拼接资料
                context_texts = [f"资料{i+1}: {res['text']}" for i, res in enumerate(rag_results)]
                rag_context_str = "\n".join(context_texts)
                
                # 【关键一步】把资料“喂”给 LLM
                # 我们通过修改 query，把背景知识强行塞进 prompt
                # 这样即使不改 Strategy 的代码，LLM 也能看到这些知识
                enhanced_query = f"""
请基于以下参考资料回答用户问题：
【参考资料】
{rag_context_str}

【用户问题】
{query}
"""
            else:
                logger.info("[RAG] 未找到相关资料，使用纯模型回答")
                enhanced_query = query
                
        except Exception as e:
            logger.error(f"[RAG] 检索出错 (降级为纯模型模式): {e}")
            enhanced_query = query
        # =====================================================
        
        # 2. 选择策略
        strategy = self.strategies[intent]
        
        # 3. 执行策略 (注意：这里传入的是 enhanced_query，包含了上下文)
        logger.info("[Strategy] 开始生成回答...")
        context = {
            "user_id": user_id,
            "parent_id": parent_id,
        }
        # 这里的 enhanced_query 会带着“宫保鸡丁做法”传给 ModelScope
        response = await strategy.process(enhanced_query, context)
        
        # 4. 生成对话 ID
        conversation_id = str(uuid.uuid4())
        response.conversation_id = conversation_id
        response.parent_id = parent_id
        
        # 5. 保存到 Neo4j (注意：这里我们保存原始 query，不保存很长的 prompt)
        logger.info("[DB] 正在保存对话到 Neo4j...")
        try:
            # 创建用户节点
            user_node_id = f"{conversation_id}_user"
            await neo4j_client.save_dialogue_node(
                node_id=user_node_id,
                user_id=user_id,
                role="user",
                content=query,  # 保存用户的原始提问
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
            
            # 建立链接
            await neo4j_client.link_dialogue_nodes(
                parent_node_id=user_node_id,
                child_node_id=ai_node_id
            )
            
            if parent_id:
                await neo4j_client.link_dialogue_nodes(
                    parent_node_id=parent_id,
                    child_node_id=user_node_id
                )
        except Exception as e:
            logger.error(f"[DB] Neo4j 保存失败: {str(e)}")
            # 即使存数据库失败，也先返回回答给用户
        
        # 6. 提取知识三元组 (异步后台执行)
        logger.info("[Knowledge] 触发三元组提取...")
        knowledge_triples = await self.extract_knowledge_triples(
            query=query,
            answer=response.answer,
            conversation_id=conversation_id,
            user_id=user_id
        )
        response.knowledge_triples = knowledge_triples
        
        return response
    
    async def process_recursive_query(
        self,
        user_id: str,
        parent_id: str,
        fragment_id: str,
        query: str
    ) -> AgentResponse:
        """处理递归追问"""
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