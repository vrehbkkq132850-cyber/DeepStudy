"""
策略基类
"""
from abc import ABC, abstractmethod
from backend.api.schemas.response import AgentResponse


class BaseStrategy(ABC):
    """策略基类"""
    
    @abstractmethod
    async def process(
        self,
        query: str,
        context: dict = None
    ) -> AgentResponse:
        """
        处理查询
        
        Args:
            query: 用户查询
            context: 上下文信息
            
        Returns:
            Agent 响应
        """
        pass
