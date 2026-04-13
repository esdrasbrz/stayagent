import logging
import urllib.parse
from typing import List
from playwright.async_api import async_playwright

from app.models import SearchRequest, StayResult, PlatformEnum
from app.crawlers.base import BaseCrawler

logger = logging.getLogger(__name__)


class BookingCrawler(BaseCrawler):
    async def run(self, request: SearchRequest) -> List[StayResult]:
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
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page()

                # Use a standard user agent
                await page.set_extra_http_headers(
                    {
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36"
                    }
                )

                await page.goto(url, wait_until="domcontentloaded", timeout=30000)

                # Dismiss cookie banner if it exists
                try:
                    cookie_btn = page.locator("button#onetrust-accept-btn-handler")
                    if await cookie_btn.count() > 0:
                        await cookie_btn.click(timeout=3000)
                except Exception:
                    pass

                # Wait for property cards
                try:
                    await page.wait_for_selector(
                        'div[data-testid="property-card"]', timeout=15000
                    )
                    listings = await page.locator(
                        'div[data-testid="property-card"]'
                    ).all()
                except Exception:
                    logger.warning(
                        "Could not find Booking listing cards, page layout might have changed or got blocked."
                    )
                    listings = []

                for i, listing in enumerate(listings):
                    if i >= request.limit:
                        break

                    try:
                        name = ""
                        title_loc = listing.locator('div[data-testid="title"]')
                        if await title_loc.count() > 0:
                            name = await title_loc.first.inner_text()

                        external_url = ""
                        link_loc = listing.locator('a[data-testid="title-link"]')
                        if await link_loc.count() > 0:
                            href = await link_loc.first.get_attribute("href")
                            if href:
                                external_url = (
                                    href
                                    if href.startswith("http")
                                    else f"https://www.booking.com{href}"
                                )

                        price_total = None
                        currency = "USD"
                        price_loc = listing.locator(
                            'span[data-testid="price-and-discounted-price"]'
                        )
                        if await price_loc.count() > 0:
                            price_text = await price_loc.first.inner_text()
                            from app.crawlers.utils import parse_price_and_currency

                            price_total, currency = parse_price_and_currency(price_text)

                        rating = None
                        rating_loc = listing.locator(
                            'div[data-testid="review-score"] > div'
                        )
                        if await rating_loc.count() > 0:
                            rating_text = await rating_loc.first.inner_text()
                            try:
                                rating = float(rating_text)
                            except Exception:
                                pass

                        image_urls = []
                        img_loc = listing.locator('img[data-testid="image"]')
                        if await img_loc.count() > 0:
                            src = await img_loc.first.get_attribute("src")
                            if src:
                                image_urls.append(src)

                        results.append(
                            StayResult(
                                platform=PlatformEnum.BOOKING,
                                external_url=external_url,
                                name=name or f"Booking Listing {i}",
                                price_total=price_total,
                                rating=rating,
                                image_urls=image_urls,
                                currency=currency,
                            )
                        )
                    except Exception as e:
                        logger.error(f"Error parsing Booking listing: {e}")
                        continue

                await browser.close()
                return results

        except Exception as e:
            logger.error(f"Booking crawler failed: {e}")
            return results
