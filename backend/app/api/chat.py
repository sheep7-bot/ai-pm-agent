import json
import logging
from typing import Any, AsyncIterator

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from langchain_core.messages import HumanMessage
from pydantic import BaseModel

from ..agent.graph import get_graph
from ..agent.llm import chat_stream, llm_enabled
from ..db import (
    add_message,
    add_prd_version,
    create_session,
    get_latest_prd,
    get_session,
    touch_session,
)
from ..schemas import PRD

logger = logging.getLogger("aipm.api.chat")
router = APIRouter(prefix="/api", tags=["chat"])


class ChatRequest(BaseModel):
    session_id: str | None = None
    message: str


def sse(event: str, data: dict[str, Any]) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


async def _prd_reply(final_prd: dict, mode: str, change_summary: str) -> AsyncIterator[str]:
    name = final_prd.get("product_name", "产品")
    if not llm_enabled():
        yield f"（未配置 LLM Key，返回占位结果）已{'修订' if mode == 'revise' else '生成'}「{name}」的 PRD。{change_summary}"
        return
    summary = json.dumps(
        {
            "product_name": name,
            "one_liner": final_prd.get("one_liner"),
            "features": [f.get("name") for f in final_prd.get("features", [])][:8],
            "changed": change_summary,
        },
        ensure_ascii=False,
    )
    system = (
        "你是资深 AI 产品经理助手。用简洁、专业的中文，2-4 句话向用户说明本轮结果："
        f"已完成{'PRD 修订' if mode == 'revise' else 'PRD 生成'}，点出亮点，并给出下一步建议。"
        "不要输出 JSON，不要暴露你的内部推理过程。"
    )
    async for tok in chat_stream(system, f"本轮结果摘要：{summary}"):
        yield tok


async def _chat_reply(message: str) -> AsyncIterator[str]:
    """闲聊/无关内容：正常对话，不生成 PRD。"""
    if not llm_enabled():
        yield "你好，我是 AI 产品经理助手。把你的产品想法告诉我，我就能帮你生成一份结构化 PRD。"
        return
    system = (
        "你是 AI 产品经理助手（PRD/OS）。用户这次发的是寒暄、提问或与产品无关的内容。"
        "请用简短、友好、专业的中文直接回应（1-3 句），不要生成 PRD、不要罗列功能。"
        "如果合适，自然地邀请用户描述一个产品想法。不要暴露内部推理过程。"
    )
    async for tok in chat_stream(system, message):
        yield tok


async def _run(session_id: str, message: str) -> AsyncIterator[str]:
    graph = get_graph()
    config = {"configurable": {"thread_id": session_id}}
    mode = "create"
    final_prd: dict | None = None
    change_summary = ""
    changed_sections: list[str] = []
    events: list[dict] = []

    try:
        has_prd = await get_latest_prd(session_id) is not None
        inputs: dict[str, Any] = {
            "messages": [HumanMessage(content=message)],
            "session_id": session_id,
            "user_message": message,
            "has_prd": has_prd,
        }
        async for chunk in graph.astream(inputs, config=config, stream_mode="updates"):
            for _node, update in chunk.items():
                if not isinstance(update, dict):
                    continue
                if update.get("mode"):
                    mode = update["mode"]
                for ev in update.get("events", []) or []:
                    events.append(ev)
                    yield sse("step", ev)
                if update.get("prd"):
                    final_prd = update["prd"]
                if update.get("change_summary"):
                    change_summary = update["change_summary"]
                if update.get("changed_sections"):
                    changed_sections = update["changed_sections"]

        if final_prd:
            row = await add_prd_version(session_id, final_prd, change_summary, changed_sections)
            yield sse(
                "prd",
                {
                    "version": row.version,
                    "data": final_prd,
                    "change_summary": change_summary,
                    "changed_sections": changed_sections,
                },
            )

        gen = _chat_reply(message) if mode == "chat" else _prd_reply(final_prd or {}, mode, change_summary)
        reply_parts: list[str] = []
        async for tok in gen:
            reply_parts.append(tok)
            yield sse("message_delta", {"text": tok})
        reply = "".join(reply_parts)

        await add_message(session_id, "user", message)
        await add_message(session_id, "assistant", reply, events)
        if mode == "create" and final_prd:
            await touch_session(session_id, title=final_prd.get("product_name") or message[:20])
        else:
            await touch_session(session_id)

        yield sse("done", {"session_id": session_id, "mode": mode})
    except Exception as e:  # noqa: BLE001
        logger.exception("Agent 执行失败")
        yield sse("error", {"message": str(e)})


@router.post("/chat")
async def chat(req: ChatRequest) -> StreamingResponse:
    session_id = req.session_id
    if not session_id or not await get_session(session_id):
        s = await create_session(title=req.message[:20])
        session_id = s.id
    has_prd = await get_latest_prd(session_id) is not None

    async def gen() -> AsyncIterator[str]:
        yield sse("session", {"session_id": session_id, "mode": "revise" if has_prd else "create"})
        async for ev in _run(session_id, req.message):
            yield ev

    return StreamingResponse(
        gen(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no", "Connection": "keep-alive"},
    )
