from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import settings


class Base(DeclarativeBase):
    pass


engine = create_engine(settings.database_url)
SessionLocal = sessionmaker(bind=engine)


def init_db() -> None:
    from app import models  # noqa: F401 — 모델 등록

    Base.metadata.create_all(engine)


def get_session() -> Session:
    return SessionLocal()
