from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from models import Base
import logging

def update_database_schema():
    try:
        engine = create_engine('sqlite:///ships.db')
        Base.metadata.create_all(engine)
        with engine.connect() as conn:
            result = conn.execute(text("PRAGMA table_info(paths)"))
            columns = [row[1] for row in result.fetchall()]
            if columns and 'port_path' not in columns:
                conn.execute(text("ALTER TABLE paths ADD COLUMN port_path TEXT"))
            if columns and 'container_path_id' not in columns:
                conn.execute(text("ALTER TABLE paths ADD COLUMN container_path_id INTEGER"))
            conn.commit()
        return engine
    except Exception as e:
        logging.error(f"更新数据库表结构失败: {str(e)}")
        raise

engine = create_engine('sqlite:///ships.db')
Session = sessionmaker(bind=engine) 