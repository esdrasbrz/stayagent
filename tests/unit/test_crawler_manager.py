"""Tests for CrawlerManager lifecycle and context isolation."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.crawlers.manager import CrawlerManager


@pytest.mark.asyncio
class TestCrawlerManagerLifecycle:
    async def test_setup_initializes_playwright_and_browser(self):
        manager = CrawlerManager()

        mock_browser = AsyncMock()
        mock_playwright = AsyncMock()
        mock_playwright.chromium.launch = AsyncMock(return_value=mock_browser)

        with patch("app.crawlers.manager.async_playwright") as mock_ap:
            mock_ap_instance = AsyncMock()
            mock_ap_instance.start = AsyncMock(return_value=mock_playwright)
            mock_ap.return_value = mock_ap_instance

            await manager.setup()

            mock_ap_instance.start.assert_awaited_once()
            mock_playwright.chromium.launch.assert_awaited_once_with(headless=True)
            assert manager._browser is mock_browser
            assert manager._playwright is mock_playwright

    async def test_shutdown_closes_browser_and_stops_playwright(self):
        manager = CrawlerManager()
        mock_browser = AsyncMock()
        mock_playwright = AsyncMock()
        manager._browser = mock_browser
        manager._playwright = mock_playwright

        await manager.shutdown()

        mock_browser.close.assert_awaited_once()
        mock_playwright.stop.assert_awaited_once()
        assert manager._browser is None
        assert manager._playwright is None

    async def test_shutdown_is_safe_when_not_setup(self):
        """Calling shutdown without setup should not raise."""
        manager = CrawlerManager()
        await manager.shutdown()  # Should not raise

    async def test_run_all_raises_if_not_setup(self):
        manager = CrawlerManager()
        with pytest.raises(RuntimeError, match="setup"):
            await manager.run_all(MagicMock())


@pytest.mark.asyncio
class TestCrawlerManagerRunAll:
    async def test_creates_context_per_crawler_and_closes_them(self):
        manager = CrawlerManager()

        # Mock browser that returns mock contexts
        mock_contexts = [AsyncMock(), AsyncMock()]
        mock_browser = AsyncMock()
        mock_browser.new_context = AsyncMock(side_effect=mock_contexts)
        manager._browser = mock_browser

        # Mock crawlers that return empty results
        mock_crawler_a = AsyncMock()
        mock_crawler_a.run = AsyncMock(return_value=[])
        mock_crawler_b = AsyncMock()
        mock_crawler_b.run = AsyncMock(return_value=[])
        manager.crawlers = [mock_crawler_a, mock_crawler_b]

        request = MagicMock()
        results = await manager.run_all(request)

        # Should have created one context per crawler
        assert mock_browser.new_context.await_count == 2

        # Each crawler should receive its own context
        mock_crawler_a.run.assert_awaited_once_with(request, mock_contexts[0])
        mock_crawler_b.run.assert_awaited_once_with(request, mock_contexts[1])

        # All contexts should be closed
        for ctx in mock_contexts:
            ctx.close.assert_awaited_once()

        assert results == []

    async def test_aggregates_results_from_multiple_crawlers(self):
        manager = CrawlerManager()

        mock_browser = AsyncMock()
        mock_browser.new_context = AsyncMock(side_effect=[AsyncMock(), AsyncMock()])
        manager._browser = mock_browser

        result_a = MagicMock()
        result_b = MagicMock()

        mock_crawler_a = AsyncMock()
        mock_crawler_a.run = AsyncMock(return_value=[result_a])
        mock_crawler_b = AsyncMock()
        mock_crawler_b.run = AsyncMock(return_value=[result_b])
        manager.crawlers = [mock_crawler_a, mock_crawler_b]

        results = await manager.run_all(MagicMock())
        assert results == [result_a, result_b]

    async def test_handles_crawler_exception_gracefully(self):
        manager = CrawlerManager()

        mock_browser = AsyncMock()
        mock_browser.new_context = AsyncMock(side_effect=[AsyncMock(), AsyncMock()])
        manager._browser = mock_browser

        result_b = MagicMock()

        mock_crawler_a = AsyncMock()
        mock_crawler_a.run = AsyncMock(side_effect=RuntimeError("boom"))
        mock_crawler_b = AsyncMock()
        mock_crawler_b.run = AsyncMock(return_value=[result_b])
        manager.crawlers = [mock_crawler_a, mock_crawler_b]

        results = await manager.run_all(MagicMock())
        # The failed crawler's results should be skipped, not crash everything
        assert results == [result_b]
