from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from task_dispath.app.core.config import settings


class Base(DeclarativeBase):
    """SQLAlchemy Base。"""


engine = create_engine(settings.mysql_dsn, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
