import asyncio
import logging
import random
from datetime import datetime, timedelta

import httpx
from core.settings import settings

logger = logging.getLogger(__name__)


class Pinger:
    def __init__(self):
        self.failed_cycles = 0
        self.max_failed_cycles = 5
        self.disabled = False

    async def ping_url(self, url: str) -> bool:
        try:
            timeout = httpx.Timeout(60.0, connect=15.0)
            async with httpx.AsyncClient(timeout=timeout) as client:
                res = await client.get(url)
                if res.status_code == 200:
                    logger.info(f"Pinged {url} (status {res.status_code})")
                    print(f"Pinged {url} (status {res.status_code})")
                    return True
                else:
                    logger.warning(f"{url} returned status {res.status_code}")
                    print(f"{url} returned status {res.status_code}")
                    return False
        except httpx.RequestError as rqe:
            logger.warning(f"Could not reach {url}: {rqe}")
            print(f"Could not reach {url}: {rqe}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error pinging {url}: {e}")
            print(f"Unexpected error pinging {url}: {e}")
            return False

    async def lightweight_periodic_ping(self):
        while not self.disabled:
            now = datetime.now()
            hour = now.hour

            if 6 <= hour < 22:
                base_interval = 600
            else:
                base_interval = random.randint(900, 1020)

            urls = settings.CRITICAL_SERVICE_URLS
            if not urls:
                logger.warning("No URLs configured. Stopping pinger.")
                print("No URLs configured. Stopping pinger.")
                self.disabled = True
                break

            logger.info(f"Starting ping cycle for {len(urls)} URLs.")
            print(f"Checking {len(urls)} URLs:", urls)

            results = await asyncio.gather(
                *(self.ping_url(url) for url in urls if url.strip()),
                return_exceptions=True,
            )

            successful = sum(1 for r in results if r is True)
            failed = len(urls) - successful

            if successful == 0:
                self.failed_cycles += 1
                logger.warning(
                    f"All pings failed (cycle #{self.failed_cycles}/{self.max_failed_cycles})"
                )
                print(
                    f"All pings failed (cycle #{self.failed_cycles}/{self.max_failed_cycles})"
                )
                if self.failed_cycles >= self.max_failed_cycles:
                    self.disabled = True
                    logger.error("Auto-disabling pinger due to repeated failures.")
                    print("Auto-disabling pinger due to repeated failures.")
                    break
            else:
                self.failed_cycles = 0

            jitter = random.randint(-30, 30)
            next_interval = base_interval + jitter
            next_ping_time = now + timedelta(seconds=next_interval)

            logger.info(
                f"Completed ping cycle — {successful} OK, {failed} failed. "
                f"Next at {next_ping_time.strftime('%Y-%m-%d %H:%M:%S')} "
                f"(interval: {next_interval}s)"
            )
            print(
                f"Completed ping cycle — {successful} OK, {failed} failed. "
                f"Next ping at {next_ping_time.strftime('%Y-%m-%d %H:%M:%S')} "
                f"(interval: {next_interval}s)"
            )

            await asyncio.sleep(next_interval)

        logger.info("Pinger loop exited cleanly.")
        print("Pinger loop exited cleanly.")


pinger = Pinger()
