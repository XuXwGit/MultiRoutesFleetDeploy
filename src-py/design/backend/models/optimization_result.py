"""
优化结果数据模型
"""
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime

from src.backend.models.route import Route


@dataclass
class OptimizationResult:
    """优化结果数据模型"""
    
    id: str
    method: str
    routes: List[Route]
    parameters: Dict[str, Any]
    total_cost: float
    created_at: datetime = field(default_factory=datetime.now)
    execution_time: float = 0.0  # 执行时间（秒）
    iterations: int = 0
    status: str = "completed"  # completed, failed, cancelled
    metrics: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def route_count(self) -> int:
        """
        获取路线数量
        
        Returns:
            路线数量
        """
        return len(self.routes)
    
    @property
    def total_distance(self) -> float:
        """
        计算总距离
        
        Returns:
            总距离
        """
        return sum(route.total_distance for route in self.routes)
    
    @property
    def total_duration(self) -> float:
        """
        计算总时长
        
        Returns:
            总时长（天）
        """
        return sum(route.total_duration for route in self.routes)
    
    def to_dict(self) -> Dict[str, Any]:
        """
        转换为字典表示
        
        Returns:
            优化结果数据字典
        """
        return {
            'id': self.id,
            'method': self.method,
            'routes': [route.to_dict() for route in self.routes],
            'parameters': self.parameters,
            'total_cost': self.total_cost,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'execution_time': self.execution_time,
            'iterations': self.iterations,
            'status': self.status,
            'metrics': self.metrics,
            'route_count': self.route_count,
            'total_distance': self.total_distance,
            'total_duration': self.total_duration
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'OptimizationResult':
        """
        从字典创建优化结果对象
        
        Args:
            data: 优化结果数据字典
            
        Returns:
            优化结果对象
        """
        routes = [
            Route.from_dict(route_data)
            for route_data in data.get('routes', [])
        ]
        
        created_at = data.get('created_at')
        if created_at and isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at)
            
        return cls(
            id=data.get('id', ''),
            method=data.get('method', ''),
            routes=routes,
            parameters=data.get('parameters', {}),
            total_cost=data.get('total_cost', 0.0),
            created_at=created_at or datetime.now(),
            execution_time=data.get('execution_time', 0.0),
            iterations=data.get('iterations', 0),
            status=data.get('status', 'completed'),
            metrics=data.get('metrics', {})
        )