import json

from fastapi import APIRouter, HTTPException

from ..db import (
    create_session,
    get_latest_prd,
    get_messages,
    get_prd_versions,
    get_session,
    list_sessions,
)

router = APIRouter(prefix="/api", tags=["sessions"])


@router.get("/sessions")
async def api_list_sessions():
    rows = await list_sessions()
    return [
        {"id": r.id, "title": r.title, "created_at": r.created_at.isoformat(), "updated_at": r.updated_at.isoformat()}
        for r in rows
    ]


@router.post("/sessions")
async def api_create_session(title: str = "新会话"):
    r = await create_session(title)
    return {"id": r.id, "title": r.title}


@router.get("/sessions/{session_id}")
async def api_get_session(session_id: str):
    s = await get_session(session_id)
    if not s:
        raise HTTPException(404, "会话不存在")
    msgs = await get_messages(session_id)
    return {
        "id": s.id,
        "title": s.title,
        "messages": [
            {
                "id": m.id,
                "role": m.role,
                "content": m.content,
                "events": json.loads(m.events or "[]"),
                "created_at": m.created_at.isoformat(),
            }
            for m in msgs
        ],
    }


@router.get("/sessions/{session_id}/prd")
async def api_get_prd(session_id: str):
    row = await get_latest_prd(session_id)
    if not row:
        return {"version": 0, "data": None}
    return {
        "version": row.version,
        "data": json.loads(row.data),
        "change_summary": row.change_summary,
        "changed_sections": json.loads(row.changed_sections or "[]"),
        "created_at": row.created_at.isoformat(),
    }


@router.get("/sessions/{session_id}/prd/versions")
async def api_prd_versions(session_id: str):
    rows = await get_prd_versions(session_id)
    return [
        {
            "version": r.version,
            "change_summary": r.change_summary,
            "changed_sections": json.loads(r.changed_sections or "[]"),
            "created_at": r.created_at.isoformat(),
        }
        for r in rows
    ]


@router.get("/sessions/{session_id}/events")
async def api_events(session_id: str):
    msgs = await get_messages(session_id)
    out = []
    for m in msgs:
        for ev in json.loads(m.events or "[]"):
            out.append({**ev, "message_id": m.id, "at": m.created_at.isoformat()})
    return out
