import threading
import time
from collections import defaultdict, deque

from .config import settings


class FailureLimiter:
    """Sliding-window counter kept in memory. With several server processes,
    move this to Redis so the counts are shared."""

    def __init__(self, max_failures: int, window_seconds: int):
        self.max = max_failures
        self.window = window_seconds
        self._hits: dict[str, deque] = defaultdict(deque)
        self._lock = threading.Lock()

    def retry_after(self, key: str) -> int:
        now = time.monotonic()
        with self._lock:
            hits = self._hits[key]
            while hits and now - hits[0] > self.window:
                hits.popleft()
            if not hits:
                del self._hits[key]
                return 0
            if len(hits) >= self.max:
                return int(self.window - (now - hits[0])) + 1
        return 0

    def fail(self, key: str) -> None:
        with self._lock:
            self._hits[key].append(time.monotonic())

    def clear(self, key: str) -> None:
        with self._lock:
            self._hits.pop(key, None)


login_limiter = FailureLimiter(settings.login_max_attempts, settings.login_window_minutes * 60)
signup_limiter = FailureLimiter(5, 3600)
