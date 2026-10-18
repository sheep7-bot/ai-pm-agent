import json
import uuid
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from .config import get_settings
from .models import Base, MessageRow, PrdVersionRow, SessionRow

_settings = get_settings()
engine = create_async_engine(f"sqlite+aiosqlite:///{_settings.app_db_path}", echo=False)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False)


async def init_db() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def create_session(title: str = "新会话") -> SessionRow:
    async with SessionLocal() as db:
        row = SessionRow(id=str(uuid.uuid4()), title=title[:80] or "新会话")
        db.add(row)
        await db.commit()
        await db.refresh(row)
        return row


async def list_sessions() -> list[SessionRow]:
    async with SessionLocal() as db:
        res = await db.execute(select(SessionRow).order_by(SessionRow.updated_at.desc()))
        return list(res.scalars().all())


async def get_session(session_id: str) -> SessionRow | None:
    async with SessionLocal() as db:
        return await db.get(SessionRow, session_id)


async def touch_session(session_id: str, title: str | None = None) -> None:
    async with SessionLocal() as db:
        row = await db.get(SessionRow, session_id)
        if row and title:
            row.title = title[:80]
        await db.commit()


async def add_message(session_id: str, role: str, content: str, events: list[dict] | None = None) -> MessageRow:
    async with SessionLocal() as db:
        row = MessageRow(
            session_id=session_id,
            role=role,
            content=content,
            events=json.dumps(events or [], ensure_ascii=False),
        )
        db.add(row)
        await db.commit()
        await db.refresh(row)
        return row


async def get_messages(session_id: str) -> list[MessageRow]:
    async with SessionLocal() as db:
        res = await db.execute(
            select(MessageRow).where(MessageRow.session_id == session_id).order_by(MessageRow.id)
        )
        return list(res.scalars().all())


async def add_prd_version(
    session_id: str,
    data: dict[str, Any],
    change_summary: str = "",
    changed_sections: list[str] | None = None,
) -> PrdVersionRow:
    async with SessionLocal() as db:
        res = await db.execute(
            select(func.max(PrdVersionRow.version)).where(PrdVersionRow.session_id == session_id)
        )
        next_version = (res.scalar() or 0) + 1
        row = PrdVersionRow(
            session_id=session_id,
            version=next_version,
            data=json.dumps(data, ensure_ascii=False),
            change_summary=change_summary,
            changed_sections=json.dumps(changed_sections or [], ensure_ascii=False),
        )
        db.add(row)
        await db.commit()
        await db.refresh(row)
        return row


async def get_latest_prd(session_id: str) -> PrdVersionRow | None:
    async with SessionLocal() as db:
        res = await db.execute(
            select(PrdVersionRow)
            .where(PrdVersionRow.session_id == session_id)
            .order_by(PrdVersionRow.version.desc())
            .limit(1)
        )
        return res.scalar_one_or_none()


async def get_prd_versions(session_id: str) -> list[PrdVersionRow]:
    async with SessionLocal() as db:
        res = await db.execute(
            select(PrdVersionRow)
            .where(PrdVersionRow.session_id == session_id)
            .order_by(PrdVersionRow.version)
        )
        return list(res.scalars().all())
