import asyncio
import json
from dataclasses import dataclass
from collections.abc import Awaitable, Callable
from typing import Any

import httpx
from google import genai
from google.genai import errors, types


@dataclass(frozen=True)
class GeminiInteractionResult:
    answer: str
    interaction_id: str
    tool_results: tuple[dict[str, Any], ...] = ()


class GeminiInteractionError(Exception):
    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


def _sdk_error_details(error: Exception) -> tuple[str | None, bool]:
    if isinstance(error, (httpx.TimeoutException, asyncio.TimeoutError)):
        return "MODEL_TIMEOUT", True

    is_google_sdk_error = error.__class__.__module__.startswith("google.genai")
    if not isinstance(error, errors.APIError) and not is_google_sdk_error:
        return None, False

    error_name = error.__class__.__name__
    if error_name == "APITimeoutError":
        return "MODEL_TIMEOUT", True
    if error_name == "APIConnectionError":
        return "MODEL_CONNECTION_ERROR", True

    code = getattr(error, "code", None) or getattr(error, "status_code", None)
    if code == 429:
        return "MODEL_RATE_LIMITED", True
    if code in {500, 502, 503, 504}:
        return "MODEL_BUSY", True
    if code in {401, 403}:
        return "MODEL_AUTH_ERROR", False
    if code == 400:
        return "INVALID_INTERACTION_STATE", False
    return "MODEL_ERROR", False


async def create_gemini_interaction(
    *,
    api_key: str,
    model: str,
    system_instruction: str,
    input_text: str,
    previous_interaction_id: str | None,
    thinking_level: str | None,
    timeout_seconds: float,
    max_retries: int,
    tools: list[dict] | None = None,
    tool_handler: Callable[[str, dict], Awaitable[dict]] | None = None,
    max_tool_calls: int = 4,
) -> GeminiInteractionResult:
    client = genai.Client(
        api_key=api_key,
        http_options=types.HttpOptions(
            retry_options=types.HttpRetryOptions(attempts=1),
        ),
    )

    try:
        for attempt in range(max_retries + 1):
            generation_config = {"max_output_tokens": 700}
            if thinking_level:
                generation_config["thinking_level"] = thinking_level

            body = {
                "model": model,
                "input": input_text,
                "system_instruction": system_instruction,
                "store": True,
                "generation_config": generation_config,
            }
            if previous_interaction_id:
                body["previous_interaction_id"] = previous_interaction_id
            if tools:
                body["tools"] = tools

            try:
                interaction = await asyncio.wait_for(
                    client.aio.interactions.create(
                        **body,
                        timeout=timeout_seconds,
                    ),
                    timeout=timeout_seconds,
                )
                tool_results: list[dict[str, Any]] = []
                tool_call_count = 0

                while True:
                    function_calls = [
                        step
                        for step in (getattr(interaction, "steps", None) or [])
                        if getattr(step, "type", None) == "function_call"
                    ]
                    if not function_calls:
                        break
                    if not tools or tool_handler is None:
                        raise GeminiInteractionError("UNEXPECTED_TOOL_CALL")
                    if tool_call_count + len(function_calls) > max_tool_calls:
                        raise GeminiInteractionError("TOOL_CALL_LIMIT_EXCEEDED")

                    function_results = []
                    for step in function_calls:
                        name = str(getattr(step, "name", "") or "")
                        arguments = getattr(step, "arguments", None) or {}
                        call_id = str(getattr(step, "id", "") or "")
                        if not name or not call_id or not isinstance(arguments, dict):
                            raise GeminiInteractionError("INVALID_TOOL_CALL")
                        result = await tool_handler(name, arguments)
                        safe_result = result if isinstance(result, dict) else {"result": result}
                        tool_results.append({"name": name, "arguments": arguments, "result": safe_result})
                        function_results.append(
                            {
                                "type": "function_result",
                                "name": name,
                                "call_id": call_id,
                                "result": [
                                    {
                                        "type": "text",
                                        "text": json.dumps(safe_result, ensure_ascii=False),
                                    }
                                ],
                            }
                        )
                    tool_call_count += len(function_calls)
                    interaction_id = str(interaction.id or "").strip()
                    if not interaction_id:
                        raise GeminiInteractionError("EMPTY_MODEL_RESPONSE")
                    interaction = await asyncio.wait_for(
                        client.aio.interactions.create(
                            model=model,
                            input=function_results,
                            tools=tools,
                            system_instruction=system_instruction,
                            previous_interaction_id=interaction_id,
                            store=True,
                            generation_config=generation_config,
                            timeout=timeout_seconds,
                        ),
                        timeout=timeout_seconds,
                    )

                answer = (interaction.output_text or "").strip()
                interaction_id = str(interaction.id or "").strip()
                if not answer or not interaction_id:
                    raise GeminiInteractionError("EMPTY_MODEL_RESPONSE")
                return GeminiInteractionResult(
                    answer=answer,
                    interaction_id=interaction_id,
                    tool_results=tuple(tool_results),
                )
            except Exception as error:
                reason, retryable = _sdk_error_details(error)
                if reason is None:
                    raise
                if reason == "MODEL_RATE_LIMITED":
                    raise GeminiInteractionError(reason) from error
                if not retryable or attempt >= max_retries:
                    raise GeminiInteractionError(reason) from error

            await asyncio.sleep(0.4 * (2**attempt))
    finally:
        await client.aio.aclose()

    raise GeminiInteractionError("MODEL_ERROR")
