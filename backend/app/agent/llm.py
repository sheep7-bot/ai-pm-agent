import json
import logging
import uuid
from typing import AsyncIterator, Type, TypeVar

from openai import AsyncOpenAI
from pydantic import BaseModel, ValidationError

from ..config import get_settings

logger = logging.getLogger("aipm.llm")

T = TypeVar("T", bound=BaseModel)

_client: AsyncOpenAI | None = None
# opencode-go 网关要求每个会话一个稳定 session id（用于路由与 prompt 缓存）
_SESSION_ID = str(uuid.uuid4())


def get_client() -> AsyncOpenAI:
    global _client
    if _client is None:
        s = get_settings()
        headers = {"User-Agent": s.llm_user_agent, "x-opencode-session": _SESSION_ID}
        _client = AsyncOpenAI(
            api_key=s.llm_api_key or "EMPTY",
            base_url=s.llm_base_url,
            default_headers=headers,
            timeout=90.0,
            max_retries=1,
        )
    return _client


def llm_enabled() -> bool:
    return get_settings().llm_enabled


def _schema_prompt(model: Type[BaseModel]) -> str:
    schema = json.dumps(model.model_json_schema(), ensure_ascii=False)
    return (
        "你必须只输出一个合法的 JSON 对象，不要包含任何解释性文字、Markdown 代码块或多余字符。\n"
        f"JSON 必须严格符合以下 JSON Schema：\n{schema}"
    )


def _thinking(thinking: bool) -> dict:
    return {"thinking": {"type": "enabled" if thinking else "disabled"}}


async def chat_stream(system: str, user: str, thinking: bool = False) -> AsyncIterator[str]:
    """流式对话回复（用于最终自然语言回复）。"""
    s = get_settings()
    stream = await get_client().chat.completions.create(
        model=s.llm_model,
        messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
        stream=True,
        temperature=0.6,
        extra_body=_thinking(thinking),
    )
    async for chunk in stream:
        delta = chunk.choices[0].delta.content if chunk.choices else None
        if delta:
            yield delta


async def chat_json(
    system: str,
    user: str,
    model: Type[T],
    retries: int = 3,
    thinking: bool = False,
    max_tokens: int = 16000,
) -> T:
    """结构化输出：JSON 模式 + Pydantic 校验 + 重试。"""
    s = get_settings()
    messages = [
        {"role": "system", "content": f"{system}\n\n{_schema_prompt(model)}"},
        {"role": "user", "content": user},
    ]
    last_err: Exception | None = None
    for attempt in range(retries):
        resp = await get_client().chat.completions.create(
            model=s.llm_model,
            messages=messages,
            response_format={"type": "json_object"},
            temperature=0.3,
            max_tokens=max_tokens,
            extra_body=_thinking(thinking),
        )
        content = (resp.choices[0].message.content or "").strip()
        if not content:
            last_err = ValueError("模型返回空内容")
            continue
        if content.startswith("```"):
            content = content.strip("`")
            content = content[content.find("{") : content.rfind("}") + 1]
        try:
            return model.model_validate_json(content)
        except (ValidationError, json.JSONDecodeError) as e:
            last_err = e
            logger.warning("chat_json 解析失败(第%s次): %s", attempt + 1, e)
            messages.append({"role": "assistant", "content": content})
            messages.append(
                {"role": "user", "content": f"上面的 JSON 无法通过校验：{e}\n请只返回修正后的合法 JSON。"}
            )
    raise RuntimeError(f"结构化输出重试 {retries} 次仍失败: {last_err}")
