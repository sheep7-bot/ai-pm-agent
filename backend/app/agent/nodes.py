import json
import logging
from typing import Any

from .llm import chat_json, llm_enabled
from .state import AgentState, StepEvent
from .tools import run_tools
from ..schemas import PRD, Intent, ResearchPlan, RevisionResult

logger = logging.getLogger("aipm.nodes")

_GREETINGS = {
    "你好", "您好", "hi", "hello", "hey", "在吗", "在么", "哈喽", "哈罗",
    "谢谢", "多谢", "感谢", "thanks", "thank you", "测试", "test", "你是谁",
    "早上好", "晚上好", "下午好", "嗨", "在不在",
}


def _looks_like_chitchat(text: str) -> bool:
    t = text.strip().lower().strip("！!。.？?~～ ")
    return len(t) <= 12 and (t in _GREETINGS or not any(c.isalnum() for c in t))


def _ev(node: str, status: str, title: str, detail: str = "") -> StepEvent:
    return {"node": node, "status": status, "title": title, "detail": detail}


def _context(tool_results: dict[str, list[dict[str, Any]]]) -> str:
    lines: list[str] = []
    for r in tool_results.get("web", []):
        url = f" ({r.get('url')})" if r.get("url") else ""
        lines.append(f"- [竞品/市场] {r.get('title','')}{url}: {r.get('snippet','')}")
    for r in tool_results.get("knowledge", []):
        lines.append(f"- [方法论] {r.get('title','')}: {r.get('snippet','')}")
    return "\n".join(lines) if lines else "（无外部资料，请基于通用产品经验作答）"


def _stub_prd(idea: str) -> PRD:
    return PRD(
        product_name=idea[:20] or "未命名产品",
        one_liner=f"面向用户的一站式解决方案：{idea[:40]}",
        background=idea,
        goals=["验证核心需求", "形成可用 MVP"],
        target_users=[{"name": "目标用户", "description": "待补充画像", "needs": ["高效完成任务"]}],
        features=[
            {"name": "核心功能（示例）", "description": "待细化", "priority": "P0", "rationale": "MVP 闭环"},
        ],
        metrics=[{"name": "周活跃用户", "target": "待定", "how_to_measure": "埋点统计"}],
        milestones=[{"phase": "MVP", "timeline": "T+4周", "deliverables": ["可运行版本"]}],
        risks=["未配置 LLM Key，当前为占位输出"],
        open_questions=["目标用户是否需要进一步细分？"],
    )


# ---------------- nodes ----------------

async def analyze_node(state: AgentState) -> dict[str, Any]:
    """需求分析：判断意图（新产品 / 修改 PRD / 闲聊），决定 mode。"""
    text = state.get("user_message", "").strip()
    has_prd = bool(state.get("has_prd"))

    if _looks_like_chitchat(text):
        # 明显是寒暄/无内容，直接走闲聊，省一次模型调用
        mode, label = "chat", "闲聊/无关内容"
    elif not llm_enabled():
        mode = "revise" if has_prd else "create"
        label = "修订现有 PRD" if has_prd else "新建 PRD"
    else:
        intent = await chat_json(
            "你是 AI 产品经理助手的前置意图识别器。判断用户这句话属于哪类：\n"
            "- new_product：提出了一个产品/功能想法或需求\n"
            "- modify_prd：在要求修改/补充已有 PRD（如『再加个导出功能』）\n"
            "- chitchat：寒暄、闲聊、提问、与产品无关的内容\n"
            f"当前会话{'已有' if has_prd else '还没有'} PRD。",
            f"用户消息：{text}",
            Intent,
            thinking=False,
            max_tokens=200,
        )
        if intent.kind == "chitchat":
            mode, label = "chat", "闲聊/无关内容"
        elif intent.kind == "modify_prd":
            mode = "revise" if has_prd else "create"
            label = "修订现有 PRD" if has_prd else "新建 PRD"
        else:
            mode, label = "create", "新建 PRD"

    update: dict[str, Any] = {
        "mode": mode,
        "events": [_ev("analyze", "done", "需求分析", f"识别意图：{label}")],
    }
    # 只有真正要产出/修改 PRD 时，才把这句话当作产品描述沉淀
    if mode in ("create", "revise"):
        update["product_idea"] = state.get("product_idea") or text
    return update


async def plan_node(state: AgentState) -> dict[str, Any]:
    idea = state.get("product_idea", "")
    if not llm_enabled():
        plan = ResearchPlan(
            need_web_search=False,
            web_queries=[],
            need_knowledge=True,
            knowledge_queries=["prd 结构", "功能优先级"],
            plan_summary="（未配置 LLM）按默认流程：查询方法论→生成 PRD",
        )
    else:
        plan = await chat_json(
            "你是资深 AI 产品经理，负责为产品想法制定调研计划。"
            "请判断是否需要联网做竞品调研、是否需要查询 PRD 方法论知识库，并给出具体查询词。",
            f"产品想法：{idea}\n请输出调研计划。",
            ResearchPlan,
        )
    tools_used = []
    if plan.need_web_search:
        tools_used.append("web_search")
    if plan.need_knowledge:
        tools_used.append("knowledge_query")
    return {
        "plan": plan.model_dump(),
        "events": [
            _ev("planning", "done", "任务规划", f"{plan.plan_summary} | 选用工具: {', '.join(tools_used) or '无'}")
        ],
    }


async def research_node(state: AgentState) -> dict[str, Any]:
    plan = state.get("plan") or {}
    web_q = plan.get("web_queries", []) if plan.get("need_web_search") else []
    kb_q = plan.get("knowledge_queries", []) if plan.get("need_knowledge") else []
    results = await run_tools(web_q, kb_q)
    events: list[StepEvent] = []
    if web_q:
        events.append(
            _ev("research", "done", "调用工具 · 竞品搜索(Tavily)", f"查询: {', '.join(web_q)} → {len(results['web'])} 条结果")
        )
    if kb_q:
        events.append(
            _ev("research", "done", "调用工具 · 知识库查询", f"查询: {', '.join(kb_q)} → {len(results['knowledge'])} 条结果")
        )
    if not events:
        events.append(_ev("research", "done", "无需工具", "本轮跳过工具调用"))
    return {"tool_results": results, "events": events}


async def draft_prd_node(state: AgentState) -> dict[str, Any]:
    idea = state.get("product_idea", "")
    ctx = _context(state.get("tool_results") or {})
    if not llm_enabled():
        prd = _stub_prd(idea)
    else:
        prd = await chat_json(
            "你是资深 AI 产品经理。请基于产品想法与调研资料，生成一份结构化、可落地的 PRD。"
            "功能需给出 P0/P1/P2 优先级与依据；竞品需引用资料中的来源链接；指标要可度量。"
            "务必完整填充所有字段。",
            f"产品想法：{idea}\n\n调研资料：\n{ctx}\n\n请生成 PRD。",
            PRD,
            thinking=True,
        )
    return {
        "prd": prd.model_dump(),
        "change_summary": "初次生成 PRD",
        "changed_sections": ["*"],
        "events": [_ev("draft_prd", "done", "生成结构化 PRD", f"{prd.product_name}：{len(prd.features)} 项功能 / {len(prd.metrics)} 项指标")],
    }


async def revise_prd_node(state: AgentState) -> dict[str, Any]:
    current = state.get("prd") or {}
    instruction = state.get("user_message", "")
    if not llm_enabled():
        result = RevisionResult(
            prd=PRD.model_validate(current) if current else _stub_prd(instruction),
            change_summary="（未配置 LLM）占位修改",
            changed_sections=[],
        )
    else:
        plan = state.get("plan") or {}
        ctx = _context(state.get("tool_results") or {})
        result = await chat_json(
            "你是资深 AI 产品经理。用户希望在现有 PRD 上做修改。"
            "请返回修改后的完整 PRD、本次的变更说明，以及被修改的字段名列表"
            "（字段名用：background / goals / target_users / features / competitors / metrics / milestones / risks / open_questions）。"
            "未涉及的字段必须原样保留。",
            f"用户修改要求：{instruction}\n\n当前 PRD（JSON）：\n{json.dumps(current, ensure_ascii=False)}\n\n"
            f"本轮补充资料：\n{ctx}\n\n请输出修改结果。",
            RevisionResult,
            thinking=True,
        )
        _ = plan
    return {
        "prd": result.prd.model_dump(),
        "change_summary": result.change_summary,
        "changed_sections": result.changed_sections,
        "events": [
            _ev(
                "revise_prd",
                "done",
                "修订 PRD",
                f"{result.change_summary} | 涉及字段: {', '.join(result.changed_sections) or '—'}",
            )
        ],
    }
