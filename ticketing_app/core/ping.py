import asyncio
import logging
from datetime import datetime, timedelta

import httpx
from core.settings import settings

logger = logging.getLogger(__name__)


class Pinger:
    def __init__(self):
        self.failed_cycles = 0
        self.max_failed_cycles = 5
        self.disabled = False
        self.interval = 14 * 60 + 10 

    async def ping_url(self, url: str) -> bool:
        try:
            timeout = httpx.Timeout(60.0, connect=15.0)
            async with httpx.AsyncClient(timeout=timeout) as client:
                res = await client.get(url)
                if res.status_code == 200:
                    logger.info(f"Pinged {url} (status {res.status_code})")
                    return True
                elif res.status_code == 429:
                    logger.warning(f"{url} rate limited (429).")
                    return False
                else:
                    logger.warning(f"{url} returned status {res.status_code}")
                    return False
        except httpx.RequestError as rqe:
            logger.warning(f"Could not reach {url}: {rqe}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error pinging {url}: {e}")
            return False

    async def ping_all(self):
        
        urls = [url.strip() for url in settings.CRITICAL_SERVICE_URLS if url.strip()]
        results = await asyncio.gather(
            *(self.ping_url(url) for url in urls), return_exceptions=True
        )
        successful = sum(1 for r in results if r is True)
        failed = len(urls) - successful
        return successful, failed

    async def periodic_ping(self):
        while not self.disabled:
            now = datetime.now()
            successful, failed = await self.ping_all()

            if successful == 0:
                self.failed_cycles += 1
                logger.warning(
                    f"All pings failed (cycle #{self.failed_cycles}/{self.max_failed_cycles})"
                )
                if self.failed_cycles >= self.max_failed_cycles:
                    self.disabled = True
                    logger.error("Auto-disabling pinger due to repeated failures.")
                    break
            else:
                self.failed_cycles = 0

            next_ping_time = now + timedelta(seconds=self.interval)
            logger.info(
                f"Completed ping cycle — {successful} OK, {failed} failed. Next at {next_ping_time.strftime('%Y-%m-%d %H:%M:%S')}"
            )

            await asyncio.sleep(self.interval)


pinger = Pinger()
