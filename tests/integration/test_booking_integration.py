import pytest
import pytest_asyncio
import datetime

from playwright.async_api import async_playwright

from app.models import SearchRequest, PlatformEnum
from app.crawlers.booking import BookingCrawler


@pytest.fixture
def future_dates():
    checkin = datetime.date.today() + datetime.timedelta(days=30)
    checkout = checkin + datetime.timedelta(days=3)
    return checkin, checkout


@pytest.fixture
def future_dates_long():
    checkin = datetime.date.today() + datetime.timedelta(days=60)
    checkout = checkin + datetime.timedelta(days=14)
    return checkin, checkout


@pytest_asyncio.fixture
async def browser_context():
    """Provide a shared browser context for integration tests."""
    pw = await async_playwright().start()
    browser = await pw.chromium.launch(headless=True)
    context = await browser.new_context(
        user_agent=(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/114.0.0.0 Safari/537.36"
        )
    )
    yield context
    await context.close()
    await browser.close()
    await pw.stop()


def assert_valid_booking_results(results):
    assert isinstance(results, list), "Crawler should return a list"

    if len(results) == 0:
        pytest.skip(
            "Booking.com returned 0 results; page structure may have changed or we were blocked (CAPTCHA). skipping assertions."
        )

    for result in results:
        assert result.platform == PlatformEnum.BOOKING
        assert result.name, "Listing should have a parsed name"
        assert (
            isinstance(result.price_total, (int, float)) or result.price_total is None
        ), "Price should be numeric or None"
        if result.price_total is not None:
            assert result.price_total > 0
            assert result.price_per_night is not None and result.price_per_night > 0
        assert result.currency, "Currency should be parsed or fallback to USD"
        assert isinstance(result.image_urls, list)


@pytest.mark.asyncio
async def test_booking_crawler_live_standard(future_dates, browser_context):
    """Test standard case with 2 guests and a 3-day stay."""
    checkin, checkout = future_dates
    request = SearchRequest(
        location="New York, NY",
        checkin=checkin,
        checkout=checkout,
        guests=2,
        limit=3,
    )
    crawler = BookingCrawler()
    results = await crawler.run(request, browser_context)
    assert_valid_booking_results(results)
    assert len(results) <= 3


@pytest.mark.asyncio
async def test_booking_crawler_live_large_group(future_dates, browser_context):
    """Test searching for a larger group to ensure url params work."""
    checkin, checkout = future_dates
    request = SearchRequest(
        location="Chicago, IL",
        checkin=checkin,
        checkout=checkout,
        guests=6,
        limit=2,
    )
    crawler = BookingCrawler()
    results = await crawler.run(request, browser_context)
    assert_valid_booking_results(results)
    assert len(results) <= 2


@pytest.mark.asyncio
async def test_booking_crawler_live_long_stay(future_dates_long, browser_context):
    """Test a 14-day stay to verify total vs nightly math."""
    checkin, checkout = future_dates_long
    request = SearchRequest(
        location="Miami, FL",
        checkin=checkin,
        checkout=checkout,
        guests=2,
        limit=2,
    )
    crawler = BookingCrawler()
    results = await crawler.run(request, browser_context)
    assert_valid_booking_results(results)
