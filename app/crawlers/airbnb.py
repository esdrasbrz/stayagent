import logging
from typing import List
import urllib.parse

from playwright.async_api import BrowserContext

from app.models import SearchRequest, StayResult, PlatformEnum
from app.crawlers.base import BaseCrawler
from app.crawlers.config import get_selectors
from app.crawlers.utils import (
    calculate_prices,
    find_first_element,
    find_first_matching,
    parse_price_and_currency,
)

logger = logging.getLogger(__name__)


class AirbnbCrawler(BaseCrawler):
    async def run(
        self, request: SearchRequest, context: BrowserContext
    ) -> List[StayResult]:
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
            page = await context.new_page()

            await page.goto(url, wait_until="domcontentloaded", timeout=30000)

            # Wait for listings using fallback selectors
            container_selectors = get_selectors("airbnb", "LISTING_CONTAINER")
            try:
                # Try primary selector for wait, then fall back
                await page.wait_for_selector(container_selectors[0], timeout=15000)
            except Exception:
                if len(container_selectors) > 1:
                    try:
                        await page.wait_for_selector(
                            container_selectors[1], timeout=5000
                        )
                    except Exception:
                        pass

            listings = await find_first_matching(page, container_selectors)
            if not listings:
                logger.warning(
                    "Could not find Airbnb listing elements, page layout might have changed or got blocked."
                )

            title_selectors = get_selectors("airbnb", "TITLE")
            price_selectors = get_selectors("airbnb", "PRICE")
            link_selectors = get_selectors("airbnb", "LINK")
            image_selectors = get_selectors("airbnb", "IMAGE")

            for i, listing in enumerate(listings):
                if i >= request.limit:
                    break

                try:
                    # Extract link
                    link_loc = await find_first_element(listing, link_selectors)
                    href = await link_loc.get_attribute("href") if link_loc else None
                    external_url = f"https://www.airbnb.com{href}" if href else ""

                    # Extract title
                    name = ""
                    title_loc = await find_first_element(listing, title_selectors)
                    if title_loc:
                        name = await title_loc.inner_text()

                    # Price and Currency extraction
                    price_per_night = None
                    price_total = None
                    currency = "USD"

                    price_loc = await find_first_element(listing, price_selectors)
                    if price_loc:
                        price_text = await price_loc.inner_text()
                        price_total, currency = parse_price_and_currency(price_text)
                        if price_total is not None:
                            price_per_night = calculate_prices(
                                price_total, request.checkin, request.checkout
                            )

                    # Image
                    image_urls = []
                    img_loc = await find_first_element(listing, image_selectors)
                    if img_loc:
                        src = await img_loc.get_attribute("src")
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

            await page.close()
            return results

        except Exception as e:
            logger.error(f"Airbnb crawler failed: {e}")
            return results
