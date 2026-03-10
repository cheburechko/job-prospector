import asyncio
import time


class RateLimiter:
    def __init__(self, rps: float = 2.0):
        self.min_interval = 1.0 / rps
        self._last_request = 0.0
        self._lock = asyncio.Lock()

    async def acquire(self):
        async with self._lock:
            wait = self.min_interval - (time.monotonic() - self._last_request)
            if wait > 0:
                await asyncio.sleep(wait)
            self._last_request = time.monotonic()
