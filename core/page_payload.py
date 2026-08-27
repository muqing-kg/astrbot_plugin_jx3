from __future__ import annotations

from typing import Any


async def read_json_payload(request: Any) -> dict[str, Any]:
    """Read JSON body from AstrBot web request.

    New AstrBot exposes ``request.json`` as an awaitable function.
    Older Quart-style request exposes it as an async property.
    """
    try:
        json_attr = getattr(request, "json", None)
        if callable(json_attr):
            data = await json_attr(default={})
        else:
            data = json_attr
            if hasattr(data, "__await__"):
                data = await data
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}
