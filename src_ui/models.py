from sqlalchemy.orm import declarative_base
from sqlalchemy import Column, Integer, String, Float, Text

Base = declarative_base()

class Ship(Base):
    __tablename__ = 'ships'
    id = Column(Integer, primary_key=True)
    name = Column(String)
    type = Column(String)
    capacity = Column(Float)
    speed = Column(Float)
    status = Column(String)
    current_port = Column(String)
    next_port = Column(String)
    eta = Column(String)
    operating_cost = Column(Float)
    route_id = Column(Integer)
    max_num = Column(Integer)

class Route(Base):
    __tablename__ = 'routes'
    id = Column(Integer, primary_key=True)
    number_of_ports = Column(Integer)
    ports = Column(Text)
    number_of_calls = Column(Integer)
    ports_of_call = Column(Text)
    times = Column(Text)

class Port(Base):
    __tablename__ = 'ports'
    id = Column(Integer, primary_key=True)
    name = Column(String)
    whether_trans = Column(Integer)
    region = Column(String)
    group = Column(Integer)

class Node(Base):
    __tablename__ = 'nodes'
    id = Column(Integer, primary_key=True)
    route = Column(Integer)
    call = Column(Integer)
    port = Column(String)
    round_trip = Column(Integer)
    time = Column(Float)

class TransshipArc(Base):
    __tablename__ = 'transship_arcs'
    id = Column(Integer, primary_key=True)
    port = Column(String)
    origin_node_id = Column(Integer)
    origin_time = Column(Float)
    transship_time = Column(Float)
    destination_node_id = Column(Integer)
    destination_time = Column(Float)
    from_route = Column(Integer)
    to_route = Column(Integer)

class TravelingArc(Base):
    __tablename__ = 'traveling_arcs'
    id = Column(Integer, primary_key=True)
    route = Column(Integer)
    origin_node_id = Column(Integer)
    origin_call = Column(Integer)
    origin_port = Column(String)
    round_trip = Column(Integer)
    origin_time = Column(Float)
    traveling_time = Column(Float)
    destination_node_id = Column(Integer)
    destination_call = Column(Integer)
    destination_port = Column(String)
    destination_time = Column(Float)

class Path(Base):
    __tablename__ = 'paths'
    id = Column(Integer, primary_key=True)
    origin_port = Column(String)
    origin_time = Column(Integer)
    destination_port = Column(String)
    destination_time = Column(Integer)
    path_time = Column(Integer)
    transship_port = Column(String)
    transship_time = Column(String)
    port_path_length = Column(Integer)
    port_path = Column(String)
    arcs_length = Column(Integer)
    arcs_id = Column(String)
    container_path_id = Column(Integer)

    def get_transship_port_list(self):
        return [] if self.transship_port == '0' else self.transship_port.split(',')

    def get_transship_time_list(self):
        return [] if self.transship_time == '0' else [int(x) for x in self.transship_time.split(',')]

    def get_port_path_list(self):
        return [] if self.port_path == '0' else self.port_path.split(',')

    def get_arcs_id_list(self):
        return [] if self.arcs_id == '0' else [int(x) for x in self.arcs_id.split(',')]

class VesselPath(Base):
    __tablename__ = 'vessel_paths'
    id = Column(Integer, primary_key=True)
    vessel_route_id = Column(Integer)
    number_of_arcs = Column(Integer)
    arcs_id = Column(String)
    origin_time = Column(Integer)
    destination_time = Column(Integer)

class Request(Base):
    __tablename__ = 'requests'
    id = Column(Integer, primary_key=True)
    origin_port = Column(String)
    destination_port = Column(String)
    laden_paths = Column(String)
    empty_paths = Column(String)
    earliest_pickup_time = Column(Float)
    latest_destination_time = Column(Float)
    number_of_laden_path = Column(Integer)
    number_of_empty_path = Column(Integer)
    laden_paths = Column(String)
    empty_paths = Column(String)

    def get_laden_paths_list(self):
        return [] if self.laden_paths == '0' else [int(x) for x in self.laden_paths.split(',')]

    def get_empty_paths_list(self):
        return [] if self.empty_paths == '0' else [int(x) for x in self.empty_paths.split(',')]

class DemandRange(Base):
    __tablename__ = 'demand_range'
    id = Column(Integer, primary_key=True, autoincrement=True)
    origin_region = Column(Integer)
    destination_region = Column(Integer)
    demand_lower_bound = Column(Integer)
    demand_upper_bound = Column(Integer)
    freight_lower_bound = Column(Integer)
    freight_upper_bound = Column(Integer)

class PortGeo(Base):
    __tablename__ = 'port_geo'
    id = Column(Integer, primary_key=True)
    city_en = Column(String)
    # name  = Column(String)
    region = Column(String)
    latitude = Column(Float)
    longitude = Column(Float) 