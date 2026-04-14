import asyncio
import logging
from typing import List, Optional

from playwright.async_api import async_playwright, Playwright, Browser

from app.models import SearchRequest, StayResult
from app.crawlers.airbnb import AirbnbCrawler
from app.crawlers.booking import BookingCrawler

logger = logging.getLogger(__name__)

# Standard user-agent shared across all crawler contexts
_DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/114.0.0.0 Safari/537.36"
)


class CrawlerManager:
    """
    Manages a shared Playwright browser instance and dispatches crawl jobs
    with isolated BrowserContext objects for data separation.
    """

    def __init__(self) -> None:
        self.crawlers = [AirbnbCrawler(), BookingCrawler()]
        self._playwright: Optional[Playwright] = None
        self._browser: Optional[Browser] = None

    async def setup(self) -> None:
        """Initialize Playwright and launch a shared Chromium browser."""
        logger.info("CrawlerManager: starting Playwright and launching browser...")
        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(headless=True)
        logger.info("CrawlerManager: browser ready.")

    async def shutdown(self) -> None:
        """Close the browser and stop Playwright cleanly."""
        logger.info("CrawlerManager: shutting down...")
        if self._browser:
            await self._browser.close()
            self._browser = None
        if self._playwright:
            await self._playwright.stop()
            self._playwright = None
        logger.info("CrawlerManager: shutdown complete.")

    async def run_all(self, request: SearchRequest) -> List[StayResult]:
        """
        Runs all configured crawlers concurrently, each in an isolated BrowserContext.

        The shared browser must have been initialised via ``setup()`` before calling
        this method.
        """
        if self._browser is None:
            raise RuntimeError("CrawlerManager.setup() must be called before run_all()")

        contexts = []
        tasks = []
        for crawler in self.crawlers:
            ctx = await self._browser.new_context(user_agent=_DEFAULT_USER_AGENT)
            contexts.append(ctx)
            tasks.append(crawler.run(request, ctx))

        # gather results, returning exceptions instead of raising
        results_lists = await asyncio.gather(*tasks, return_exceptions=True)

        # Close all contexts regardless of outcome
        for ctx in contexts:
            try:
                await ctx.close()
            except Exception:
                pass

        # Aggregate successful results
        aggregated: List[StayResult] = []
        for res in results_lists:
            if isinstance(res, Exception):
                logger.error(f"Crawler failed: {res}")
            elif isinstance(res, list):
                aggregated.extend(res)

        return aggregated
