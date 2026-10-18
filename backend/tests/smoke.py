import asyncio
import json
import sys

from langchain_core.messages import HumanMessage


def log(*a):
    print(*a, flush=True)


async def main():
    log("importing app modules...")
    from app.db import init_db
    from app.agent.graph import manager, get_graph

    log("init_db...")
    await init_db()
    log("manager.startup...")
    await manager.startup()
    log("graph compiled:", type(manager.graph).__name__)

    try:
        g = get_graph()
        cfg = {"configurable": {"thread_id": "smoke-1"}}
        log("invoking graph...")
        async for chunk in g.astream(
            {
                "messages": [HumanMessage(content="做一个给宠物主人的遛狗社交App")],
                "session_id": "smoke-1",
                "user_message": "做一个给宠物主人的遛狗社交App",
                "mode": "create",
            },
            config=cfg,
            stream_mode="updates",
        ):
            for node, upd in chunk.items():
                log("NODE", node, "->", json.dumps(upd, ensure_ascii=False)[:300])
        log("done")
    finally:
        await manager.shutdown()


if __name__ == "__main__":
    try:
        asyncio.run(asyncio.wait_for(main(), timeout=240))
    except Exception as e:
        import traceback

        traceback.print_exc()
        sys.exit(1)
