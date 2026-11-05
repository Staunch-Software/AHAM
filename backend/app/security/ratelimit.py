import time
from collections import defaultdict, deque


class FailureLimiter:
    """In-process sliding-window limiter for failed attempts (e.g. logins).

    Per-process memory: with several API workers each has its own window, so the effective limit is
    multiplied. Put a shared limiter (reverse proxy or Redis) in front before scaling out.
    """

    def __init__(self, max_failures: int = 5, window_seconds: int = 900):
        self.max, self.window = max_failures, window_seconds
        self._hits: dict[str, deque[float]] = defaultdict(deque)

    def _prune(self, key: str, now: float) -> deque[float]:
        q = self._hits[key]
        while q and now - q[0] > self.window:
            q.popleft()
        if not q:
            self._hits.pop(key, None)
            return deque()
        return q

    def blocked(self, key: str) -> int:
        """Seconds until the key may try again (0 = not blocked)."""
        now = time.monotonic()
        q = self._prune(key, now)
        return 0 if len(q) < self.max else max(1, int(self.window - (now - q[0])))

    def fail(self, key: str) -> None:
        self._hits[key].append(time.monotonic())

    def clear(self, key: str) -> None:
        self._hits.pop(key, None)


login_limiter = FailureLimiter()
