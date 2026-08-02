from collections import defaultdict, deque
from time import time


class InMemorySlidingWindowLimiter:
    def __init__(self):
        self._windows: dict[str, deque[float]] = defaultdict(deque)

    def allow(self, key: str, window_seconds: int, max_count: int) -> bool:
        now = time()
        window = self._windows[key]
        while window and window[0] <= now - window_seconds:
            window.popleft()

        if len(window) >= max_count:
            return False

        window.append(now)
        return True


sliding_window_limiter = InMemorySlidingWindowLimiter()
