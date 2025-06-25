"""
航运路线数据模型
"""
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class RouteSegment:
    """路线段数据模型"""
    
    origin_port_id: str
    destination_port_id: str
    distance: float
    duration: float  # 单位：天
    cost: Optional[float] = None
    vessel_type: Optional[str] = None
    restrictions: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """
        转换为字典表示
        
        Returns:
            路线段数据字典
        """
        return {
            'origin_port_id': self.origin_port_id,
            'destination_port_id': self.destination_port_id,
            'distance': self.distance,
            'duration': self.duration,
            'cost': self.cost,
            'vessel_type': self.vessel_type,
            'restrictions': self.restrictions
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'RouteSegment':
        """
        从字典创建路线段对象
        
        Args:
            data: 路线段数据字典
            
        Returns:
            路线段对象
        """
        return cls(
            origin_port_id=data.get('origin_port_id', ''),
            destination_port_id=data.get('destination_port_id', ''),
            distance=data.get('distance', 0.0),
            duration=data.get('duration', 0.0),
            cost=data.get('cost'),
            vessel_type=data.get('vessel_type'),
            restrictions=data.get('restrictions', {})
        )


@dataclass
class Route:
    """航运路线数据模型"""
    
    id: str
    name: str
    segments: List[RouteSegment]
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: Optional[datetime] = None
    is_active: bool = True
    color: str = "blue"
    
    @property
    def total_distance(self) -> float:
        """
        计算总距离
        
        Returns:
            总距离
        """
        return sum(segment.distance for segment in self.segments)
    
    @property
    def total_duration(self) -> float:
        """
        计算总时长
        
        Returns:
            总时长（天）
        """
        return sum(segment.duration for segment in self.segments)
    
    @property
    def total_cost(self) -> float:
        """
        计算总成本
        
        Returns:
            总成本
        """
        return sum(segment.cost or 0 for segment in self.segments)
    
    @property
    def port_sequence(self) -> List[str]:
        """
        获取港口序列
        
        Returns:
            港口ID序列
        """
        if not self.segments:
            return []
            
        ports = [self.segments[0].origin_port_id]
        for segment in self.segments:
            ports.append(segment.destination_port_id)
            
        return ports
    
    def to_dict(self) -> Dict[str, Any]:
        """
        转换为字典表示
        
        Returns:
            路线数据字典
        """
        return {
            'id': self.id,
            'name': self.name,
            'segments': [segment.to_dict() for segment in self.segments],
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'is_active': self.is_active,
            'color': self.color,
            'total_distance': self.total_distance,
            'total_duration': self.total_duration,
            'total_cost': self.total_cost,
            'port_sequence': self.port_sequence
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Route':
        """
        从字典创建路线对象
        
        Args:
            data: 路线数据字典
            
        Returns:
            路线对象
        """
        segments = [
            RouteSegment.from_dict(segment_data)
            for segment_data in data.get('segments', [])
        ]
        
        created_at = data.get('created_at')
        if created_at and isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at)
            
        updated_at = data.get('updated_at')
        if updated_at and isinstance(updated_at, str):
            updated_at = datetime.fromisoformat(updated_at)
            
        return cls(
            id=data.get('id', ''),
            name=data.get('name', ''),
            segments=segments,
            created_at=created_at or datetime.now(),
            updated_at=updated_at,
            is_active=data.get('is_active', True),
            color=data.get('color', 'blue')
        ) 