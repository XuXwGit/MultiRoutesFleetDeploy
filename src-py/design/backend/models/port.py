"""
港口数据模型
"""
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field


@dataclass
class Port:
    """港口数据模型"""
    
    id: str
    name: str
    latitude: float
    longitude: float
    country: str
    capacity: Optional[float] = None
    handling_cost: Optional[float] = None
    restrictions: Dict[str, Any] = field(default_factory=dict)
    connections: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """
        转换为字典表示
        
        Returns:
            港口数据字典
        """
        return {
            'id': self.id,
            'name': self.name,
            'latitude': self.latitude,
            'longitude': self.longitude,
            'country': self.country,
            'capacity': self.capacity,
            'handling_cost': self.handling_cost,
            'restrictions': self.restrictions,
            'connections': self.connections
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Port':
        """
        从字典创建港口对象
        
        Args:
            data: 港口数据字典
            
        Returns:
            港口对象
        """
        return cls(
            id=data.get('id', ''),
            name=data.get('name', ''),
            latitude=data.get('latitude', 0.0),
            longitude=data.get('longitude', 0.0),
            country=data.get('country', ''),
            capacity=data.get('capacity'),
            handling_cost=data.get('handling_cost'),
            restrictions=data.get('restrictions', {}),
            connections=data.get('connections', [])
        ) 