import asyncio
from typing import List

from app.models import SearchRequest, StayResult
from app.crawlers.airbnb import AirbnbCrawler
from app.crawlers.booking import BookingCrawler

class CrawlerManager:
    def __init__(self):
        self.crawlers = [
            AirbnbCrawler(),
            BookingCrawler()
        ]

    async def run_all(self, request: SearchRequest) -> List[StayResult]:
        """Runs all configured crawlers concurrently and aggregates the results."""
        tasks = [crawler.run(request) for crawler in self.crawlers]
        
        # gather results, returning empty lists on exceptions to prevent total failure
        results_lists = await asyncio.gather(*tasks, return_exceptions=True)
        
        aggregated = []
        for res in results_lists:
            if isinstance(res, Exception):
                # We could log this exception more extensively here
                import logging
                logging.getLogger(__name__).error(f"Crawler failed: {res}")
            elif isinstance(res, list):
                aggregated.extend(res)
                
        return aggregated
