"""
IP-based in-memory sliding-window rate limiter middleware.

Architecture note
-----------------
This implementation uses a thread-safe in-memory store (collections.deque).
For single-process deployments this is sufficient.
For multi-process / distributed deployments replace ``_RateLimitStore`` with
a Redis-backed implementation — the interface (check / record) is unchanged.

The middleware is deliberately NOT applied globally.  Individual route
handlers opt-in by depending on the ``rate_limit_*`` dependencies defined
at the bottom of this module, which keeps test routes unrestricted.
"""

import time
import threading
from collections import defaultdict, deque
from typing import Callable, Deque, Dict, Tuple

from fastapi import HTTPException, Request, status

from src.core.config import settings


# ------------------------------------------------------------------ #
# In-memory store                                                      #
# ------------------------------------------------------------------ #

class _RateLimitStore:
    """
    Sliding-window request log per (route_key, client_ip).
    Thread-safe via a per-store lock.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        # key -> deque of timestamps (float seconds)
        self._windows: Dict[Tuple[str, str], Deque[float]] = defaultdict(deque)

    def is_allowed(self, key: Tuple[str, str], limit: int, window_seconds: int) -> bool:
        """
        Returns True if the request is within the rate limit.
        Side-effect: records this request timestamp when allowed.
        """
        now = time.monotonic()
        cutoff = now - window_seconds

        with self._lock:
            dq = self._windows[key]
            # Evict expired timestamps
            while dq and dq[0] < cutoff:
                dq.popleft()

            if len(dq) >= limit:
                return False

            dq.append(now)
            return True

    def reset(self) -> None:
        """Clear all windows — useful between tests."""
        with self._lock:
            self._windows.clear()


# Singleton store — shared across the process lifetime
_store = _RateLimitStore()


# ------------------------------------------------------------------ #
# Public helpers                                                       #
# ------------------------------------------------------------------ #

def get_client_ip(request: Request) -> str:
    """
    Extract the real client IP from the request.

    Render and most reverse proxies set X-Forwarded-For.
    We take the leftmost (client) address to avoid bypass via header injection
    (only the first hop is trustworthy when the proxy is configured correctly).
    """
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        # Take the first IP — the originating client
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def enforce_rate_limit(
    request: Request,
    route_key: str,
    limit: int,
    window_seconds: int = 60,
) -> None:
    """
    Enforce the rate limit for the given route + IP combination.
    Raises HTTP 429 if the limit is exceeded.
    Skips enforcement when RATE_LIMIT_ENABLED is False (e.g., in tests).
    """
    if not settings.RATE_LIMIT_ENABLED:
        return

    ip = get_client_ip(request)
    key = (route_key, ip)

    if not _store.is_allowed(key, limit=limit, window_seconds=window_seconds):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "error": "RATE_LIMIT_EXCEEDED",
                "message": "Too many requests. Please slow down and retry later.",
                "route": route_key,
            },
            headers={"Retry-After": str(window_seconds)},
        )


def reset_rate_limit_store() -> None:
    """Test helper — reset all counters between test cases."""
    _store.reset()
