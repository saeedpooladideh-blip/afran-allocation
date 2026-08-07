from __future__ import annotations

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.database.base import Base


class Database:
    """Small SQLAlchemy boundary that keeps storage replaceable."""

    def __init__(self, database_url: str) -> None:
        connect_args: dict[str, object] = {}
        if database_url.startswith("sqlite"):
            connect_args["check_same_thread"] = False

        self.engine: Engine = create_engine(
            database_url,
            pool_pre_ping=True,
            connect_args=connect_args,
        )
        if database_url.startswith("sqlite"):
            event.listen(self.engine, "connect", self._configure_sqlite)
        self.session_factory = sessionmaker(
            bind=self.engine,
            class_=Session,
            expire_on_commit=False,
            autoflush=False,
        )

    @staticmethod
    def _configure_sqlite(dbapi_connection: object, _: object) -> None:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.close()

    def create_schema(self) -> None:
        # Importing models registers every table on Base.metadata.
        import app.models  # noqa: F401

        Base.metadata.create_all(self.engine)

    def dispose(self) -> None:
        self.engine.dispose()
