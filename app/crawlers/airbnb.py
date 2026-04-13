import logging
from typing import List
from playwright.async_api import async_playwright
import urllib.parse

from app.models import SearchRequest, StayResult, PlatformEnum
from app.crawlers.base import BaseCrawler
from app.crawlers.utils import (
    calculate_prices,
    parse_price_and_currency,
)

logger = logging.getLogger(__name__)


class AirbnbCrawler(BaseCrawler):
    async def run(self, request: SearchRequest) -> List[StayResult]:
        results: List[StayResult] = []

        location_encoded = urllib.parse.quote(request.location)
        url = (
            f"https://www.airbnb.com/s/{location_encoded}/homes"
            f"?checkin={request.checkin.isoformat()}"
            f"&checkout={request.checkout.isoformat()}"
            f"&adults={request.guests}"
        )
        logger.info(f"Airbnb Crawler starting for: {url}")

        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page()
                # Use a standard user agent to avoid basic blocks
                await page.set_extra_http_headers(
                    {
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36"
                    }
                )

                await page.goto(url, wait_until="domcontentloaded", timeout=30000)

                # Wait for listings to load (usually airbnb listings have itemprop="itemListElement" or standard listing cards)
                # We'll use a broad sector for the listing cards here. This selector often changes.
                try:
                    await page.wait_for_selector(
                        'div[itemprop="itemListElement"]', timeout=15000
                    )
                    listings = await page.locator(
                        'div[itemprop="itemListElement"]'
                    ).all()
                except Exception:
                    logger.warning(
                        "Could not find Airbnb listing elements, page layout might have changed or got blocked."
                    )
                    listings = []

                for i, listing in enumerate(listings):
                    if i >= request.limit:
                        break

                    try:
                        # Extract basic info
                        # Note: These selectors are highly volatile and illustrative. We try to grab the first anchor.
                        link_locator = listing.locator("a").first
                        href = await link_locator.get_attribute("href")
                        external_url = f"https://www.airbnb.com{href}" if href else ""

                        # Name/Title usually inside a meta tag or specific span
                        name = ""
                        title_loc = listing.locator(
                            'div[data-testid="listing-card-title"]'
                        )
                        if await title_loc.count() > 0:
                            name = await title_loc.first.inner_text()

                        # Price and Currency extraction
                        price_per_night = None
                        price_total = None
                        currency = "USD"

                        price_loc = listing.locator(
                            'span:has-text("$"), span:has-text("€"), span:has-text("£"), span:has-text("R$")'
                        )
                        if await price_loc.count() > 0:
                            price_text = await price_loc.first.inner_text()
                            price_total, currency = parse_price_and_currency(price_text)
                            if price_total is not None:
                                price_per_night = calculate_prices(
                                    price_total, request.checkin, request.checkout
                                )

                        # Image
                        image_urls = []
                        img_loc = listing.locator("img")
                        if await img_loc.count() > 0:
                            src = await img_loc.first.get_attribute("src")
                            if src:
                                image_urls.append(src)

                        results.append(
                            StayResult(
                                platform=PlatformEnum.AIRBNB,
                                external_url=external_url,
                                name=name or f"Airbnb Listing {i}",
                                price_total=price_total,
                                price_per_night=price_per_night,
                                image_urls=image_urls,
                                currency=currency,
                            )
                        )
                    except Exception as e:
                        logger.error(f"Error parsing Airbnb listing: {e}")
                        continue

                await browser.close()
                return results

        except Exception as e:
            logger.error(f"Airbnb crawler failed: {e}")
            return results
