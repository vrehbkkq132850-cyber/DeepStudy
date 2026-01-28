"""
Agent 编排器
使用自定义 LLM 客户端编排对话流程
"""
import uuid
import logging
import json
from typing import AsyncGenerator, Optional

from backend.agent.llm_client import ModelScopeLLMClient
from backend.agent.intent_router import IntentRouter, IntentType
from backend.agent.strategies import DerivationStrategy, CodeStrategy, ConceptStrategy
from backend.agent.prompts.system_prompts import RECURSIVE_PROMPT
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
            api_base=settings.MODELSCOPE_API_BASE,
        )
        logger.info("主模型初始化成功")

        logger.info(f"初始化 Coder 模型: {settings.CODER_MODEL_NAME}")
        self.coder_llm = ModelScopeLLMClient(
            model_name=settings.CODER_MODEL_NAME,
            api_key=settings.MODELSCOPE_API_KEY,
            api_base=settings.MODELSCOPE_API_BASE,
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

    async def process_query(
        self,
        user_id: str,
        query: str,
        parent_id: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> AgentResponse:
        """
        处理用户查询（非流式路径，保留以兼容旧逻辑）
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

        # 保存到 Neo4j（降级模式：失败只记录日志，不阻断返回）
        logger.info("开始保存到 Neo4j...")
        try:
            # 创建用户节点
            user_node_id = f"{conversation_id}_user"
            await neo4j_client.save_dialogue_node(
                node_id=user_node_id,
                user_id=user_id,
                role="user",
                content=query,
                intent=intent.value if intent else None,
            )

            # 创建 AI 节点
            ai_node_id = conversation_id
            await neo4j_client.save_dialogue_node(
                node_id=ai_node_id,
                user_id=user_id,
                role="assistant",
                content=response.answer,
                intent=intent.value if intent else None,
            )

            # 创建用户到 AI 的关系
            await neo4j_client.link_dialogue_nodes(
                parent_node_id=user_node_id,
                child_node_id=ai_node_id,
            )

            # 如果有父节点，创建父节点到用户节点的关系
            if parent_id:
                logger.info(f"创建父节点关系: parent_id={parent_id}")
                await neo4j_client.link_dialogue_nodes(
                    parent_node_id=parent_id,
                    child_node_id=user_node_id,
                )
            logger.info("Neo4j 保存成功")
        except Exception as e:
            # 降级：只记录错误，不中断主流程
            logger.warning(
                "保存对话到 Neo4j 失败（已降级处理，不影响主流程）: %s", str(e), exc_info=True
            )

        return response

    async def process_query_stream(
        self,
        user_id: str,
        query: str,
        parent_id: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> AsyncGenerator[str, None]:
        """
        处理用户查询（流式输出）

        返回一个异步生成器，按行输出 JSON 字符串：
        - 第一行: {\"type\":\"meta\",\"conversation_id\":...}
        - 后续多行: {\"type\":\"delta\",\"text\":...}
        - 结束行: {\"type\":\"end\"}
        """
        logger.info(f"[stream] 开始处理查询: query={query[:50]}...")
        logger.info("[stream] 识别意图...")
        intent = await self.intent_router.route(query)
        logger.info(f"[stream] 识别结果: {intent.value}")

        strategy = self.strategies[intent]
        context = {
            "user_id": user_id,
            "parent_id": parent_id,
        }

        # 生成对话 ID，并提前下发给前端
        conversation_id = str(uuid.uuid4())
        logger.info(f"[stream] 生成对话 ID: {conversation_id}")

        # 缓存完整回答，用于流结束后写入 Neo4j
        answer_parts: list[str] = []

        # 首包：meta 信息
        meta_payload = {"type": "meta", "conversation_id": conversation_id}
        yield json.dumps(meta_payload, ensure_ascii=False) + "\n"

        try:
            # 调用策略的流式接口
            async for delta in strategy.process_stream(query, context):  # type: ignore[attr-defined]
                if not delta:
                    continue
                answer_parts.append(delta)
                payload = {"type": "delta", "text": delta}
                yield json.dumps(payload, ensure_ascii=False) + "\n"
        except Exception as e:
            logger.error("[stream] LLM 流式生成失败: %s", str(e), exc_info=True)
            error_payload = {"type": "error", "message": str(e)}
            yield json.dumps(error_payload, ensure_ascii=False) + "\n"
        finally:
            # 结束标记
            yield json.dumps({"type": "end"}, ensure_ascii=False) + "\n"

            # 在后台保存到 Neo4j（降级模式）
            full_answer = "".join(answer_parts)
            logger.info("[stream] 开始保存流式回答到 Neo4j...")
            try:
                user_node_id = f"{conversation_id}_user"
                await neo4j_client.save_dialogue_node(
                    node_id=user_node_id,
                    user_id=user_id,
                    role="user",
                    content=query,
                    intent=intent.value if intent else None,
                )

                ai_node_id = conversation_id
                await neo4j_client.save_dialogue_node(
                    node_id=ai_node_id,
                    user_id=user_id,
                    role="assistant",
                    content=full_answer,
                    intent=intent.value if intent else None,
                )

                await neo4j_client.link_dialogue_nodes(
                    parent_node_id=user_node_id,
                    child_node_id=ai_node_id,
                )

                if parent_id:
                    logger.info("[stream] 创建父节点关系: parent_id=%s", parent_id)
                    await neo4j_client.link_dialogue_nodes(
                        parent_node_id=parent_id,
                        child_node_id=user_node_id,
                    )
                logger.info("[stream] Neo4j 保存成功")
            except Exception as e:
                logger.warning(
                    "[stream] 保存流式对话到 Neo4j 失败（已降级处理）: %s",
                    str(e),
                    exc_info=True,
                )

    async def process_recursive_query(
        self,
        user_id: str,
        parent_id: str,
        fragment_id: str,
        query: str,
    ) -> AgentResponse:
        """
        处理递归追问（非流式）
        """
        # TODO: 获取父对话上下文
        # TODO: 获取片段内容

        # 使用递归提示词
        prompt = f"{RECURSIVE_PROMPT}\n\n用户追问: {query}\n\n请针对性地回答："

        response_text = await self.llm.acomplete(prompt)
        answer = response_text.text if hasattr(response_text, "text") else str(
            response_text
        )

        return AgentResponse(
            answer=answer,
            fragments=[],
            knowledge_triples=[],
            conversation_id=str(uuid.uuid4()),
            parent_id=parent_id,
        )

