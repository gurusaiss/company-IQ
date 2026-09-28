import logging
from typing import Optional

from groq import AsyncGroq, RateLimitError
from tenacity import (
    before_sleep_log,
    retry,
    retry_if_not_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from ..config import settings

logger = logging.getLogger(__name__)

# Tried in order. Separate models draw from separate daily token
# quotas on GROQ, so one exhausted model doesn't take every request
# down with it.
MODEL_CHAIN = [settings.GROQ_MODEL, settings.GROQ_FALLBACK_MODEL, settings.GROQ_FALLBACK_MODEL_2]


@retry(
    stop=stop_after_attempt(2),
    wait=wait_exponential(multiplier=1, min=2, max=6),
    retry=retry_if_not_exception_type(RateLimitError),
    before_sleep=before_sleep_log(logger, logging.WARNING),
    reraise=True,
)
async def _call_model(
    client: AsyncGroq,
    model: str,
    messages: list,
    max_tokens: int,
    temperature: float,
    use_search: bool,
) -> str:
    kwargs = {}
    if use_search:
        kwargs["tools"] = [{"type": "browser_search"}]
        kwargs["tool_choice"] = "auto"
    response = await client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
        **kwargs,
    )
    return response.choices[0].message.content or ""


async def chat_completion(
    messages: list,
    max_tokens: int,
    temperature: float = 0.25,
    use_search: bool = False,
) -> str:
    """Chat completion with automatic fallover across MODEL_CHAIN."""
    client = AsyncGroq(api_key=settings.GROQ_API_KEY, timeout=25.0)
    last_exc: Optional[Exception] = None
    for model in MODEL_CHAIN:
        try:
            return await _call_model(client, model, messages, max_tokens, temperature, use_search)
        except Exception as exc:
            logger.warning("GROQ model %s failed: %s", model, exc)
            last_exc = exc
    raise ValueError(f"All GROQ models failed: {last_exc}") from last_exc
