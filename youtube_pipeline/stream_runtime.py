from __future__ import annotations

from typing import Any

try:
    from streamz import Stream
except ImportError:  # pragma: no cover
    Stream = Any  # type: ignore[misc,assignment]


def require_streamz() -> None:
    if Stream is Any:
        raise ImportError(
            "streamz is not installed. Install it with: pip install streamz"
        )


__all__ = ["Stream", "require_streamz"]
