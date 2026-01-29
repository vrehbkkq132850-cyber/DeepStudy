"""
意图识别与路由
识别用户意图（推导/代码/概念），调用不同的处理策略
"""
from enum import Enum
from typing import Dict, Any, Protocol
from backend.config import settings


class LLM(Protocol):
    """
    LLM 协议接口
    兼容 llama-index 0.10.x 的 LLM 接口
    """
    async def acomplete(self, prompt: str):
        """
        完成文本生成
        
        Args:
            prompt: 输入提示词
            
        Returns:
            响应对象（包含 text 属性）
        """
        ...


class IntentType(str, Enum):
    """意图类型"""
    DERIVATION = "derivation"  # 推导型
    CODE = "code"  # 代码型
    CONCEPT = "concept"  # 概念型


class IntentRouter:
    """
    意图路由器
    使用 Few-shot 提示词识别用户意图
    """
    
    def __init__(self, llm: LLM):
        """
        初始化意图路由器
        
        Args:
            llm: 大语言模型实例
        """
        self.llm = llm
        self.few_shot_examples = self._get_few_shot_examples()
    
    def _get_few_shot_examples(self) -> str:
        """获取 Few-shot 示例"""
        return """
示例1:
问题: "为什么矩阵的特征值等于其行列式的值？"
意图: derivation

示例2:
问题: "用 Python 实现快速排序"
意图: code

示例3:
问题: "什么是 Schur 分解？"
意图: concept
"""
    
    async def route(self, query: str) -> IntentType:
        """
        识别用户意图（缺省实现：总是返回 CONCEPT）
        
        Args:
            query: 用户查询
            
        Returns:
            意图类型（当前缺省返回 CONCEPT）
        
        TODO: 后续可以实现真正的 Few-shot 意图识别
        """
        # 缺省实现：暂时跳过 LLM 调用，直接返回 CONCEPT
        # 保留代码结构，便于后续完善
        return IntentType.CONCEPT
