import asyncio
import json
import logging
import re
from functools import lru_cache
from pathlib import Path
from typing import Any

from ..config import get_settings

logger = logging.getLogger("aipm.tools")

_KB_PATH = Path(__file__).parent / "knowledge_base.json"

_CJK = re.compile(r"[\u4e00-\u9fff]")
_LATIN = re.compile(r"[a-zA-Z0-9]+")


@lru_cache
def _load_kb() -> list[dict[str, Any]]:
    return json.loads(_KB_PATH.read_text(encoding="utf-8"))


def _grams(text: str) -> list[str]:
    text = text.lower()
    grams = _LATIN.findall(text)
    cjk = _CJK.findall(text)
    grams += [cjk[i] + cjk[i + 1] for i in range(len(cjk) - 1)]
    return grams or [text]


def knowledge_query(query: str, top_k: int = 3) -> list[dict[str, Any]]:
    """本地 PRD 方法论/知识库检索（无需外部 Key）。"""
    q_grams = _grams(query)
    scored: list[tuple[float, dict[str, Any]]] = []
    for entry in _load_kb():
        hay = f"{entry['title']} {entry['title']} {' '.join(entry['tags'])} {' '.join(entry['tags'])} {entry['content']}".lower()
        score = sum(1 for g in q_grams if g and g in hay)
        if score > 0:
            scored.append((score, entry))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [
        {
            "title": e["title"],
            "snippet": e["content"],
            "url": None,
            "source": "knowledge",
        }
        for _, e in scored[:top_k]
    ]


def _tavily_search(query: str, max_results: int) -> list[dict[str, Any]]:
    from tavily import TavilyClient

    client = TavilyClient(api_key=get_settings().tavily_api_key)
    resp = client.search(query=query, max_results=max_results, search_depth="basic")
    out = []
    for r in resp.get("results", []):
        out.append(
            {
                "title": r.get("title", ""),
                "snippet": r.get("content", ""),
                "url": r.get("url"),
                "source": "web",
            }
        )
    return out


async def web_search(query: str, max_results: int = 4) -> list[dict[str, Any]]:
    """联网竞品/市场搜索（Tavily）。无 Key 时优雅降级。"""
    if not get_settings().search_enabled:
        return [
            {
                "title": "（竞价搜索未启用）",
                "snippet": "未配置 TAVILY_API_KEY，本次跳过联网竞品调研。",
                "url": None,
                "source": "web",
            }
        ]
    try:
        return await asyncio.to_thread(_tavily_search, query, max_results)
    except Exception as e:  # noqa: BLE001
        logger.warning("Tavily 搜索失败: %s", e)
        return [
            {
                "title": "（搜索失败）",
                "snippet": f"联网搜索出错，已跳过：{e}",
                "url": None,
                "source": "web",
            }
        ]


async def run_tools(web_queries: list[str], knowledge_queries: list[str]) -> dict[str, list[dict[str, Any]]]:
    """并发执行两个工具，返回分类结果。"""
    web_results: list[dict[str, Any]] = []
    if web_queries:
        batches = await asyncio.gather(*(web_search(q) for q in web_queries[:4]))
        for b in batches:
            web_results.extend(b)

    kb_results: list[dict[str, Any]] = []
    for q in knowledge_queries[:4]:
        kb_results.extend(knowledge_query(q))

    return {"web": web_results, "knowledge": kb_results}
