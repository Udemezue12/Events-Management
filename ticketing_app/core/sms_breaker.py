import logging
import time
from collections import deque
from typing import Any, Awaitable, Callable, Deque, Optional

from fastapi import HTTPException

logger = logging.getLogger("sms_breaker")


class SMSCircuitBreaker:
    def __init__(
        self,
        failure_threshold: int = 3,
        base_recovery_time: int = 10,
        max_recovery_time: int = 120,
        enable_retry_queue: bool = True,
    ):
        self.failure_count = 0
        self.failure_threshold = failure_threshold
        self.base_recovery_time = base_recovery_time
        self.max_recovery_time = max_recovery_time
        self.last_failure_time = 0
        self.state = "CLOSED"
        self.retry_queue: Optional[Deque[Any]] = (
            deque() if enable_retry_queue else None
        )

    
    @property
    def current_recovery_time(self):
        if self.failure_count < self.failure_threshold:
            return self.base_recovery_time

        return min(
            self.base_recovery_time
            * (2 ** (self.failure_count - self.failure_threshold)),
            self.max_recovery_time,
        )


    def _open(self):
        self.state = "OPEN"
        self.last_failure_time = time.time()
        logger.warning(
            f"🚨 SMS circuit opened after {self.failure_count} failures."
        )

    def _half_open(self):
        self.state = "HALF_OPEN"
        logger.info("🟡 SMS circuit half-open: testing SMS provider...")

    def _close(self):
        self.state = "CLOSED"
        self.failure_count = 0
        logger.info("🟢 SMS circuit closed: SMS provider stable again.")

    # ---------------------------------
    # ASYNC CALL
    # ---------------------------------

    async def async_call(
        self,
        func: Callable[..., Awaitable[Any]],
        *args,
        **kwargs,
    ) -> Any:

        now = time.time()

        if self.state == "OPEN":
            cooldown = self.current_recovery_time
            elapsed = now - self.last_failure_time

            if elapsed < cooldown:
                raise HTTPException(
                    status_code=503,
                    detail=f"SMS service temporarily unavailable. Retry in {cooldown - elapsed:.1f}s",
                )
            else:
                self._half_open()

        try:
            result = await func(*args, **kwargs)
            self._close()

            if self.retry_queue:
                await self._async_flush_retry_queue()

            return result

        except HTTPException as http_exc:
            if http_exc.status_code < 500:
                raise http_exc

            self._register_failure(http_exc)
            raise http_exc

        except Exception as e:
            self._register_failure(e)

            if self.retry_queue is not None:
                self.retry_queue.append((func, args, kwargs))
                logger.info(
                    f"📬 Queued failed SMS ({len(self.retry_queue)} pending)"
                )

            raise e


    def sync_call(
        self,
        func: Callable[..., Any],
        *args,
        **kwargs,
    ) -> Any:

        now = time.time()

        if self.state == "OPEN":
            cooldown = self.current_recovery_time
            elapsed = now - self.last_failure_time

            if elapsed < cooldown:
                raise HTTPException(
                    status_code=503,
                    detail=f"SMS service temporarily unavailable. Retry in {cooldown - elapsed:.1f}s",
                )
            else:
                self._half_open()

        try:
            result = func(*args, **kwargs)
            self._close()

            if self.retry_queue:
                self._sync_flush_retry_queue()

            return result

        except HTTPException as http_exc:
            if http_exc.status_code < 500:
                raise http_exc

            self._register_failure(http_exc)
            raise http_exc

        except Exception as e:
            self._register_failure(e)

            if self.retry_queue is not None:
                self.retry_queue.append((func, args, kwargs))
                logger.info(
                    f"📬 Queued failed SMS ({len(self.retry_queue)} pending)"
                )

            raise e

   

    def _register_failure(self, error):
        self.failure_count += 1
        logger.error(
            f"❌ SMS send failed ({self.failure_count}/{self.failure_threshold}): {error}"
        )

        if self.failure_count >= self.failure_threshold:
            self._open()


    async def _async_flush_retry_queue(self):
        logger.info("🔁 Flushing queued SMS (async)...")

        while self.retry_queue:
            func, args, kwargs = self.retry_queue.popleft()
            try:
                await func(*args, **kwargs)
                logger.info("✅ Retried SMS successfully.")
            except Exception as e:
                logger.error(f"Retry failed again: {e}")
                self.retry_queue.appendleft((func, args, kwargs))
                break

    

    def _sync_flush_retry_queue(self):
        logger.info("🔁 Flushing queued SMS (sync)...")

        while self.retry_queue:
            func, args, kwargs = self.retry_queue.popleft()
            try:
                func(*args, **kwargs)
                logger.info("✅ Retried SMS successfully.")
            except Exception as e:
                logger.error(f"Retry failed again: {e}")
                self.retry_queue.appendleft((func, args, kwargs))
                break




sms_breaker = SMSCircuitBreaker(
    failure_threshold=3,
    base_recovery_time=15,
    max_recovery_time=120,
    enable_retry_queue=True,
)