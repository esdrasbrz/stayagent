import logging
import urllib.parse
from typing import List

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


class BookingCrawler(BaseCrawler):
    async def run(
        self, request: SearchRequest, context: BrowserContext
    ) -> List[StayResult]:
        results: List[StayResult] = []

        location_encoded = urllib.parse.quote(request.location)
        url = (
            f"https://www.booking.com/searchresults.html"
            f"?ss={location_encoded}"
            f"&checkin={request.checkin.isoformat()}"
            f"&checkout={request.checkout.isoformat()}"
            f"&group_adults={request.guests}"
        )
        logger.info(f"Booking.com Crawler starting for: {url}")

        try:
            page = await context.new_page()

            await page.goto(url, wait_until="domcontentloaded", timeout=30000)

            # Dismiss cookie banner if it exists
            cookie_selectors = get_selectors("booking", "COOKIE_BANNER")
            try:
                cookie_loc = await find_first_element(page, cookie_selectors)
                if cookie_loc:
                    await cookie_loc.click(timeout=3000)
            except Exception:
                pass

            # Wait for property cards using fallback selectors
            container_selectors = get_selectors("booking", "LISTING_CONTAINER")
            try:
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
                    "Could not find Booking listing cards, page layout might have changed or got blocked."
                )

            title_selectors = get_selectors("booking", "TITLE")
            title_link_selectors = get_selectors("booking", "TITLE_LINK")
            price_selectors = get_selectors("booking", "PRICE")
            rating_selectors = get_selectors("booking", "RATING")
            image_selectors = get_selectors("booking", "IMAGE")

            for i, listing in enumerate(listings):
                if i >= request.limit:
                    break

                try:
                    # Extract title
                    name = ""
                    title_loc = await find_first_element(listing, title_selectors)
                    if title_loc:
                        name = await title_loc.inner_text()

                    # Extract link
                    external_url = ""
                    link_loc = await find_first_element(listing, title_link_selectors)
                    if link_loc:
                        href = await link_loc.get_attribute("href")
                        if href:
                            external_url = (
                                href
                                if href.startswith("http")
                                else f"https://www.booking.com{href}"
                            )

                    # Extract price
                    price_total = None
                    price_per_night = None
                    currency = "USD"
                    price_loc = await find_first_element(listing, price_selectors)
                    if price_loc:
                        price_text = await price_loc.inner_text()
                        price_total, currency = parse_price_and_currency(price_text)
                        if price_total is not None:
                            price_per_night = calculate_prices(
                                price_total, request.checkin, request.checkout
                            )

                    # Extract rating
                    rating = None
                    rating_loc = await find_first_element(listing, rating_selectors)
                    if rating_loc:
                        rating_text = await rating_loc.inner_text()
                        try:
                            rating = float(rating_text)
                        except Exception:
                            pass

                    # Extract image
                    image_urls = []
                    img_loc = await find_first_element(listing, image_selectors)
                    if img_loc:
                        src = await img_loc.get_attribute("src")
                        if src:
                            image_urls.append(src)

                    results.append(
                        StayResult(
                            platform=PlatformEnum.BOOKING,
                            external_url=external_url,
                            name=name or f"Booking Listing {i}",
                            price_total=price_total,
                            price_per_night=price_per_night,
                            rating=rating,
                            image_urls=image_urls,
                            currency=currency,
                        )
                    )
                except Exception as e:
                    logger.error(f"Error parsing Booking listing: {e}")
                    continue

            await page.close()
            return results

        except Exception as e:
            logger.error(f"Booking crawler failed: {e}")
            return results
