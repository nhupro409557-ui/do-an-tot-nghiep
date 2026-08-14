import asyncio
from dataclasses import dataclass

import httpx


GROQ_CHAT_COMPLETIONS_URL = "https://api.groq.com/openai/v1/chat/completions"


@dataclass(frozen=True)
class GroqInteractionResult:
    answer: str
    response_id: str


class GroqInteractionError(Exception):
    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


def _http_error_details(error: httpx.HTTPStatusError) -> tuple[str, bool]:
    status_code = error.response.status_code
    if status_code == 429:
        return "MODEL_RATE_LIMITED", False
    if status_code in {500, 502, 503, 504}:
        return "MODEL_BUSY", True
    if status_code in {401, 403}:
        return "MODEL_AUTH_ERROR", False
    if status_code == 400:
        return "INVALID_MODEL_REQUEST", False
    return "MODEL_ERROR", False


async def create_groq_chat_completion(
    *,
    api_key: str,
    model: str,
    system_instruction: str,
    input_text: str,
    timeout_seconds: float,
    max_retries: int,
    max_completion_tokens: int,
    reasoning_effort: str | None,
) -> GroqInteractionResult:
    body = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_instruction},
            {"role": "user", "content": input_text},
        ],
        "temperature": 0.7,
        "max_completion_tokens": max_completion_tokens,
        "top_p": 1,
        "stream": False,
    }
    if reasoning_effort:
        body["reasoning_effort"] = reasoning_effort

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    async with httpx.AsyncClient(timeout=timeout_seconds) as client:
        for attempt in range(max_retries + 1):
            try:
                response = await asyncio.wait_for(
                    client.post(
                        GROQ_CHAT_COMPLETIONS_URL,
                        headers=headers,
                        json=body,
                    ),
                    timeout=timeout_seconds,
                )
                response.raise_for_status()
                try:
                    payload = response.json()
                except ValueError as error:
                    raise GroqInteractionError("EMPTY_MODEL_RESPONSE") from error
                if not isinstance(payload, dict):
                    raise GroqInteractionError("EMPTY_MODEL_RESPONSE")
                choices = payload.get("choices") or []
                if not isinstance(choices, list):
                    raise GroqInteractionError("EMPTY_MODEL_RESPONSE")
                first_choice = choices[0] if choices else None
                message = first_choice.get("message") if isinstance(first_choice, dict) else None
                if message is not None and not isinstance(message, dict):
                    raise GroqInteractionError("EMPTY_MODEL_RESPONSE")
                answer = str((message or {}).get("content") or "").strip()
                if not answer:
                    raise GroqInteractionError("EMPTY_MODEL_RESPONSE")
                return GroqInteractionResult(
                    answer=answer,
                    response_id=str(payload.get("id") or ""),
                )
            except GroqInteractionError:
                raise
            except (httpx.TimeoutException, asyncio.TimeoutError) as error:
                if attempt >= max_retries:
                    raise GroqInteractionError("MODEL_TIMEOUT") from error
            except httpx.HTTPStatusError as error:
                reason, retryable = _http_error_details(error)
                if not retryable or attempt >= max_retries:
                    raise GroqInteractionError(reason) from error
            except httpx.RequestError as error:
                if attempt >= max_retries:
                    raise GroqInteractionError("MODEL_CONNECTION_ERROR") from error

            await asyncio.sleep(0.4 * (2**attempt))

    raise GroqInteractionError("MODEL_ERROR")
