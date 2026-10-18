"""In-memory sliding-window rate limits for endpoints that spend API credit.

One process, no shared store: enough for the single free Render instance. It
resets on restart, which is acceptable for a demo-scale app.
"""

import threading
import time
from collections import deque


class RateLimiter:
    def __init__(self, per_client: int, client_window_s: float, total: int, total_window_s: float,
                 clock=time.monotonic):
        self.per_client, self.client_window = per_client, client_window_s
        self.total, self.total_window = total, total_window_s
        self.clock = clock
        self._clients: dict[str, deque] = {}
        self._all: deque = deque()
        self._lock = threading.Lock()

    @staticmethod
    def _trim(q: deque, cutoff: float) -> None:
        while q and q[0] <= cutoff:
            q.popleft()

    def allow(self, client: str) -> bool:
        now = self.clock()
        with self._lock:
            self._trim(self._all, now - self.total_window)
            q = self._clients.setdefault(client, deque())
            self._trim(q, now - self.client_window)
            if len(q) >= self.per_client or len(self._all) >= self.total:
                return False
            q.append(now)
            self._all.append(now)
            if len(self._clients) > 10_000:  # forget idle clients
                for key in [k for k, v in self._clients.items() if not v]:
                    del self._clients[key]
            return True


def client_ip(headers, fallback: str) -> str:
    """The address Render's proxy saw: the last X-Forwarded-For entry (earlier
    entries are whatever the client sent and can be faked)."""
    forwarded = headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[-1].strip()
    return fallback
