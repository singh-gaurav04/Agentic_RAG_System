from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from sqlalchemy import JSON, String, Text, create_engine, select
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker

from src.config.settings import Settings
from src.schemas.agent_schema import ChatMessage


class Base(DeclarativeBase):
    pass


class EpisodicMemoryRecord(Base):
    __tablename__ = "episodic_memory"
    session_id: Mapped[str] = mapped_column(String, primary_key=True)
    created_at: Mapped[str] = mapped_column(String, primary_key=True)
    message_json: Mapped[dict[str, Any]] = mapped_column(JSON)


class SemanticMemoryRecord(Base):
    __tablename__ = "semantic_memory"
    session_id: Mapped[str] = mapped_column(String, primary_key=True)
    summary: Mapped[str] = mapped_column(Text)
    updated_at: Mapped[str] = mapped_column(String)


class TraceRecord(Base):
    __tablename__ = "traces"
    session_id: Mapped[str] = mapped_column(String, primary_key=True)
    created_at: Mapped[str] = mapped_column(String, primary_key=True)
    trace_json: Mapped[dict[str, Any]] = mapped_column(JSON)


class MemoryStore:
    def __init__(self, settings: Settings) -> None:
        self._database_url: str = settings.postgres_dsn
        self._engine = create_engine(self._database_url, future=True)
        self._session_factory = sessionmaker(bind=self._engine, class_=Session, expire_on_commit=False)
        self._initialize_tables()

    def _create_session(self) -> Session:
        return self._session_factory()

    def _initialize_tables(self) -> None:
        Base.metadata.create_all(self._engine)

    def append_message(self, session_id: str, message: ChatMessage) -> None:
        record: EpisodicMemoryRecord = EpisodicMemoryRecord(
            session_id=session_id,
            created_at=datetime.utcnow().isoformat(),
            message_json=message.model_dump(mode="json"),
        )
        with self._create_session() as session:
            session.add(record)
            session.commit()

    def get_recent_messages(self, session_id: str, limit: int = 8) -> list[ChatMessage]:
        statement = (
            select(EpisodicMemoryRecord.message_json)
            .where(EpisodicMemoryRecord.session_id == session_id)
            .order_by(EpisodicMemoryRecord.created_at.desc())
            .limit(limit)
        )
        with self._create_session() as session:
            rows: list[dict[str, Any]] = list(session.execute(statement).scalars().all())
        return [ChatMessage.model_validate(row) for row in reversed(rows)]

    def upsert_semantic_summary(self, session_id: str, summary: str) -> None:
        with self._create_session() as session:
            record: SemanticMemoryRecord | None = session.get(SemanticMemoryRecord, session_id)
            if record is None:
                record = SemanticMemoryRecord(
                    session_id=session_id,
                    summary=summary,
                    updated_at=datetime.utcnow().isoformat(),
                )
                session.add(record)
            else:
                record.summary = summary
                record.updated_at = datetime.utcnow().isoformat()
            session.commit()

    def get_semantic_summary(self, session_id: str) -> str:
        with self._create_session() as session:
            record: SemanticMemoryRecord | None = session.get(SemanticMemoryRecord, session_id)
            if record is None:
                return ""
            return record.summary

    def append_trace(self, session_id: str, trace: dict[str, object]) -> None:
        record: TraceRecord = TraceRecord(
            session_id=session_id,
            created_at=datetime.utcnow().isoformat(),
            trace_json=trace,
        )
        with self._create_session() as session:
            session.add(record)
            session.commit()

    def get_traces(self, session_id: str) -> list[dict[str, object]]:
        statement = (
            select(TraceRecord.trace_json)
            .where(TraceRecord.session_id == session_id)
            .order_by(TraceRecord.created_at.asc())
        )
        with self._create_session() as session:
            rows: list[dict[str, Any]] = list(session.execute(statement).scalars().all())
        return [json.loads(json.dumps(row)) for row in rows]
