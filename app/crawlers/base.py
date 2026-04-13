from abc import ABC, abstractmethod
from typing import List
from app.models import SearchRequest, StayResult


class BaseCrawler(ABC):
    """Abstract base class for all platform crawlers."""

    @abstractmethod
    async def run(self, request: SearchRequest) -> List[StayResult]:
        """Runs the crawler and returns a list of parsed results."""
        pass
