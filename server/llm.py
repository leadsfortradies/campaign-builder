"""Claude calls for the step handlers.

Every call goes through complete_json(ctx, ...) so it always uses the model
picked in the web app (ctx.model) and its token usage is recorded on the job.
"""

import json
import os
import re
import time

_client = None


class LLMError(RuntimeError):
    pass


def _get_client():
    global _client
    if _client is None:
        if not os.environ.get("ANTHROPIC_API_KEY"):
            raise LLMError("ANTHROPIC_API_KEY isn't set on the server.")
        import anthropic
        _client = anthropic.Anthropic(timeout=180.0, max_retries=1)
    return _client


def _call(model, system, user, max_tokens):
    """Returns (text, input_tokens, output_tokens). Patched in tests."""
    resp = _get_client().messages.create(
        model=model,
        max_tokens=max_tokens,
        system=system,
        messages=[{"role": "user", "content": user}],  # user: str, or a list of content blocks (images)
    )
    text = "".join(b.text for b in resp.content if getattr(b, "type", "") == "text")
    return text, resp.usage.input_tokens, resp.usage.output_tokens


def _parse_json(text):
    text = text.strip()
    fence = re.search(r"```(?:json)?\s*(.*?)```", text, re.S)
    if fence:
        text = fence.group(1).strip()
    starts = [i for i in (text.find("{"), text.find("[")) if i != -1]
    if not starts:
        raise ValueError("no JSON in response")
    start = min(starts)
    end = max(text.rfind("}"), text.rfind("]"))
    return json.loads(text[start:end + 1])


def image_block(jpeg_bytes):
    """Content block for _call/complete_json when a prompt includes a photo."""
    import base64
    return {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg",
                                        "data": base64.b64encode(jpeg_bytes).decode()}}


def complete_json(ctx, system, user, max_tokens=8000, attempts=3):
    """Ask Claude for a JSON answer. Retries on API errors and bad JSON."""
    last = None
    for i in range(attempts):
        try:
            text, tin, tout = _call(ctx.model, system, user, max_tokens)
            ctx.add_usage(tin, tout)
            return _parse_json(text)
        except LLMError:
            raise
        except Exception as exc:  # noqa: BLE001 - API hiccup or malformed JSON
            last = exc
            ctx.log(f"Claude call failed (attempt {i + 1}/{attempts}): {exc}")
            time.sleep(2 * (i + 1))
    raise LLMError(f"Claude call failed after {attempts} attempts: {last}")
