"""
ModelScope OpenAI 兼容 API 客户端
使用 OpenAI SDK 调用 ModelScope API
属于 Agent Layer
"""
import logging
from openai import AsyncOpenAI

logger = logging.getLogger(__name__)


class ModelScopeLLMClient:
    """
    ModelScope LLM 客户端
    使用 OpenAI 兼容 API，避免下载本地模型
    """
    
    def __init__(
        self,
        model_name: str,
        api_key: str,
        api_base: str
    ):
        """
        初始化 LLM 客户端
        
        Args:
            model_name: 模型名称（如 'Qwen/Qwen3-32B'）
            api_key: ModelScope API Key
            api_base: API 基础 URL
        """
        self.model_name = model_name
        self.client = AsyncOpenAI(
            base_url=api_base.rstrip('/'),
            api_key=api_key
        )
        logger.info(f"ModelScopeLLMClient 初始化: model={model_name}, api_base={api_base}")
    
    async def acomplete(self, prompt: str) -> "LLMResponse":
        """
        异步完成文本生成
        
        Args:
            prompt: 输入提示词
            
        Returns:
            LLMResponse 对象（兼容 llama-index 接口）
        """
        try:
            logger.info(f"调用 ModelScope API: model={self.model_name}")
            
            response = await self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {
                        'role': 'user',
                        'content': prompt
                    }
                ],
                temperature=0.7,
                max_tokens=2000,
                stream=False,  # 非流式，简化处理
                extra_body={
                    "enable_thinking": False  # ModelScope API 要求：非流式调用必须设置为 False
                }
            )
            
            # 提取回答内容
            content = response.choices[0].message.content
            logger.info(f"API 调用成功，返回长度: {len(content) if content else 0}")
            
            return LLMResponse(text=content or "")
        except Exception as e:
            logger.error(f"LLM API 调用失败: {str(e)}", exc_info=True)
            raise RuntimeError(f"LLM API 调用失败: {str(e)}") from e
    
    async def astream(self, prompt: str):
        """
        异步流式生成文本
        
        Args:
            prompt: 输入提示词
        
        Yields:
            每次产生一小段新增文本
        """
        logger.info(f"调用 ModelScope API（stream）: model={self.model_name}")
        try:
            stream = await self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {
                        "role": "user",
                        "content": prompt,
                    }
                ],
                temperature=0.7,
                max_tokens=2000,
                stream=True,
                extra_body={
                    "enable_thinking": False,
                },
            )
            async for chunk in stream:
                delta = chunk.choices[0].delta
                text = getattr(delta, "content", None)
                if text:
                    yield text
        except Exception as e:
            logger.error(f"LLM 流式 API 调用失败: {str(e)}", exc_info=True)
            raise RuntimeError(f"LLM API 调用失败: {str(e)}") from e
    
    async def close(self):
        """关闭客户端"""
        # OpenAI 客户端不需要显式关闭
        pass


class LLMResponse:
    """
    LLM 响应对象
    兼容 llama-index 的响应格式
    """
    def __init__(self, text: str):
        self.text = text
    
    def __str__(self):
        return self.text
