import logging
from typing import Any

from langgraph.graph import END, START, StateGraph

from .nodes import (
    analyze_node,
    draft_prd_node,
    plan_node,
    research_node,
    revise_prd_node,
)
from .state import AgentState
from ..config import get_settings

logger = logging.getLogger("aipm.graph")


def _route_after_analyze(state: AgentState) -> str:
    mode = state.get("mode") or "create"
    if mode == "chat":
        return "chat"
    return "revise" if mode == "revise" else "create"


def build_graph(checkpointer: Any = None):
    g = StateGraph(AgentState)
    g.add_node("analyze", analyze_node)
    g.add_node("planning", plan_node)
    g.add_node("research", research_node)
    g.add_node("draft_prd", draft_prd_node)
    g.add_node("revise_prd", revise_prd_node)

    g.add_edge(START, "analyze")
    g.add_conditional_edges(
        "analyze",
        _route_after_analyze,
        {"chat": END, "create": "planning", "revise": "revise_prd"},
    )
    g.add_edge("planning", "research")
    g.add_edge("research", "draft_prd")
    g.add_edge("draft_prd", END)
    g.add_edge("revise_prd", END)
    return g.compile(checkpointer=checkpointer)


class GraphManager:
    """持有编译后的图与 checkpointer 生命周期（短期记忆）。"""

    def __init__(self) -> None:
        self.graph = None
        self._conn = None

    async def startup(self) -> None:
        settings = get_settings()
        try:
            import aiosqlite
            from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

            self._conn = await aiosqlite.connect(settings.checkpoint_db_path)
            saver = AsyncSqliteSaver(self._conn)
            await saver.setup()
            self.graph = build_graph(saver)
            logger.info("checkpointer: AsyncSqliteSaver (%s)", settings.checkpoint_db_path)
        except Exception as e:  # noqa: BLE001
            logger.warning("SQLite checkpointer 初始化失败，降级为内存记忆: %s", e)
            await self.shutdown()
            from langgraph.checkpoint.memory import MemorySaver

            self.graph = build_graph(MemorySaver())

    async def shutdown(self) -> None:
        if self._conn is not None:
            await self._conn.close()
            self._conn = None


manager = GraphManager()


def get_graph():
    if manager.graph is None:
        raise RuntimeError("图尚未初始化，请检查 FastAPI lifespan")
    return manager.graph
