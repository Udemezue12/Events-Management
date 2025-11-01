import logging
import time
from collections import deque
from typing import Any, Awaitable, Callable, Deque, Optional

logger = logging.getLogger(__name__)


class CircuitBreaker:
    def __init__(
        self,
        failure_threshold: int = 3,
        base_recovery_time: int = 10,
        max_recovery_time: int = 60,
        enable_retry_queue: bool = False,
    ):
        self.failure_count = 0
        self.failure_threshold = failure_threshold
        self.base_recovery_time = base_recovery_time
        self.max_recovery_time = max_recovery_time
        self.last_failure_time = 0
        self.state = "CLOSED"
        self.retry_queue: Optional[Deque[any]] = deque() if enable_retry_queue else None

    @property
    def current_recovery_time(self):
        return min(
            self.base_recovery_time
            * (2 ** (self.failure_count - self.failure_threshold)),
            self.max_recovery_time,
        )

    def _open(self):
        self.state = "OPEN"
        self.last_failure_time = time.time()
        logger.warning(f"Circuit opened after {self.failure_count} failures.")

    def _half_open(self):
        self.state = "HALF_OPEN"
        logger.info("Circuit half-open: testing...")

    def _close(self):
        self.state = "CLOSED"
        self.failure_count = 0
        logger.info("Circuit closed: stable again.")

    async def call(self, func: Callable[..., Awaitable[Any]], *args, **kwargs) -> Any:
        now = time.time()

        if self.state == "OPEN":
            cooldown = self.current_recovery_time
            if now - self.last_failure_time < cooldown:
                raise Exception(
                    f"CircuitBreaker: still open, retry after {cooldown - (now - self.last_failure_time):.1f}s"
                )
            else:
                self._half_open()

        try:
            result = await func(*args, **kwargs)
            self._close()

            if self.retry_queue:
                await self._flush_retry_queue()
            return result

        except Exception as e:
            self.failure_count += 1
            logger.error(f" CircuitBreaker call failed ({self.failure_count}): {e}")
            if self.failure_count >= self.failure_threshold:
                self._open()

            if self.retry_queue is not None:
                self.retry_queue.append((func, args, kwargs))
                logger.info(
                    f"Queued failed operation ({len(self.retry_queue)} pending)."
                )
            raise e

    async def _flush_retry_queue(self):
        while self.retry_queue:
            func, args, kwargs = self.retry_queue.popleft()
            try:
                await func(*args, **kwargs)
                logger.info("Retried queued operation successfully.")
            except Exception as e:
                logger.error(f"Retry failed: {e}")
                self.retry_queue.appendleft((func, args, kwargs))
                break


breaker = CircuitBreaker(
    failure_threshold=3, base_recovery_time=10, enable_retry_queue=True
)
