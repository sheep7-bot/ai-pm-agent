import operator
from typing import Annotated, Any, TypedDict

from langgraph.graph.message import add_messages


class StepEvent(TypedDict):
    node: str
    status: str  # running | done | error
    title: str
    detail: str


class AgentState(TypedDict, total=False):
    # 短期记忆：由 checkpointer 按 thread_id 持久化，实现多轮上下文
    messages: Annotated[list, add_messages]

    # 本轮输入
    session_id: str
    user_message: str
    mode: str  # create | revise | chat
    has_prd: bool

    # 规划产物
    product_idea: str
    plan: dict[str, Any] | None

    # 工具产物
    tool_results: dict[str, list[dict[str, Any]]]

    # 长期产物（PRD）
    prd: dict[str, Any] | None
    change_summary: str
    changed_sections: list[str]

    # 执行流程事件（累加）
    events: Annotated[list[StepEvent], operator.add]
