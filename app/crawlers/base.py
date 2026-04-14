from abc import ABC, abstractmethod
from typing import List

from playwright.async_api import BrowserContext

from app.models import SearchRequest, StayResult


class BaseCrawler(ABC):
    """Abstract base class for all platform crawlers."""

    @abstractmethod
    async def run(
        self, request: SearchRequest, context: BrowserContext
    ) -> List[StayResult]:
        """Runs the crawler using the provided browser context and returns parsed results."""
        pass
