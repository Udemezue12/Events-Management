import asyncio
import logging
import random
from datetime import datetime, timedelta

import httpx
from core.settings import settings

logger = logging.getLogger(__name__)


class SmartPinger:
    def __init__(self):
        self.disabled = False
        self.interval = 14 * 60 + 10
        self.url_backoff = {}

    async def ping_url(self, url: str) -> bool:
        backoff_until = self.url_backoff.get(url)
        if backoff_until and datetime.now() < backoff_until:
            logger.info(f"Skipping {url}, in backoff until {backoff_until}")
            return False

        try:
            timeout = httpx.Timeout(60.0, connect=15.0)
            async with httpx.AsyncClient(timeout=timeout) as client:
                res = await client.get(url)
                if res.status_code == 200:
                    logger.info(f"Pinged {url} (status {res.status_code})")
                    return True
                elif res.status_code == 429:
                    backoff_seconds = 120 + int(180 * random.random())
                    self.url_backoff[url] = datetime.now() + timedelta(
                        seconds=backoff_seconds
                    )
                    logger.warning(
                        f"{url} rate limited (429). Backing off for {backoff_seconds}s"
                    )
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

    async def ping_url_loop(self, url: str):
        
        while not self.disabled:
            await self.ping_url(url)

            sleep_time = self.interval + random.randint(-5, 5)
            await asyncio.sleep(sleep_time)

    async def start(self):
        urls = [url.strip() for url in settings.CRITICAL_SERVICE_URLS if url.strip()]
        if not urls:
            logger.warning("No URLs configured. Pinger disabled.")
            return

        tasks = [asyncio.create_task(self.ping_url_loop(url)) for url in urls]
        logger.info(f"Started ping loops for {len(tasks)} URLs.")
        await asyncio.gather(*tasks)


pinger = SmartPinger()
