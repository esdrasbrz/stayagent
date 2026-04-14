"""Tests for the centralized SelectorRegistry and fallback utilities."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from app.crawlers.config import SELECTORS, get_selectors
from app.crawlers.utils import find_first_matching, find_first_element


# ─── SelectorRegistry Tests ─────────────────────────────────────────────────


class TestGetSelectors:
    def test_returns_list_for_known_platform_and_field(self):
        result = get_selectors("airbnb", "LISTING_CONTAINER")
        assert isinstance(result, list)
        assert len(result) > 0

    def test_returns_list_for_booking_platform(self):
        result = get_selectors("booking", "TITLE")
        assert isinstance(result, list)
        assert len(result) > 0

    def test_raises_key_error_for_unknown_platform(self):
        with pytest.raises(KeyError, match="No selectors registered"):
            get_selectors("unknown_platform", "TITLE")

    def test_raises_key_error_for_unknown_field(self):
        with pytest.raises(KeyError, match="No selectors registered"):
            get_selectors("airbnb", "NONEXISTENT_FIELD")

    def test_all_platforms_have_listing_container(self):
        """Every registered platform must define a LISTING_CONTAINER selector."""
        for platform in SELECTORS:
            selectors = get_selectors(platform, "LISTING_CONTAINER")
            assert (
                len(selectors) >= 1
            ), f"Platform '{platform}' has no LISTING_CONTAINER selectors"

    def test_all_selector_values_are_non_empty_strings(self):
        """Every individual selector string should be non-empty."""
        for platform, fields in SELECTORS.items():
            for field, selector_list in fields.items():
                for selector in selector_list:
                    assert (
                        isinstance(selector, str) and len(selector) > 0
                    ), f"Empty selector found at {platform}.{field}"


# ─── Fallback Utility Tests ─────────────────────────────────────────────────


def _make_parent_mock(match_map: dict):
    """
    Create a mock parent locator.

    ``match_map`` maps selector strings to the count of matching elements.
    If the count is > 0, locator.all() returns that many mock locators.
    """
    parent = MagicMock()

    def locator_side_effect(selector):
        loc = AsyncMock()
        count = match_map.get(selector, 0)
        loc.count = AsyncMock(return_value=count)
        loc.all = AsyncMock(return_value=[MagicMock() for _ in range(count)])
        loc.first = MagicMock() if count > 0 else None
        return loc

    parent.locator = MagicMock(side_effect=locator_side_effect)
    return parent


@pytest.mark.asyncio
class TestFindFirstMatching:
    async def test_returns_elements_from_first_match(self):
        parent = _make_parent_mock({"sel_a": 0, "sel_b": 3})
        result = await find_first_matching(parent, ["sel_a", "sel_b"])
        assert len(result) == 3

    async def test_prefers_earlier_selector(self):
        parent = _make_parent_mock({"sel_a": 2, "sel_b": 5})
        result = await find_first_matching(parent, ["sel_a", "sel_b"])
        assert len(result) == 2

    async def test_returns_empty_when_nothing_matches(self):
        parent = _make_parent_mock({"sel_a": 0, "sel_b": 0})
        result = await find_first_matching(parent, ["sel_a", "sel_b"])
        assert result == []

    async def test_returns_empty_for_empty_selector_list(self):
        parent = _make_parent_mock({})
        result = await find_first_matching(parent, [])
        assert result == []


@pytest.mark.asyncio
class TestFindFirstElement:
    async def test_returns_first_locator_on_match(self):
        parent = _make_parent_mock({"sel_a": 0, "sel_b": 2})
        result = await find_first_element(parent, ["sel_a", "sel_b"])
        assert result is not None

    async def test_returns_none_when_nothing_matches(self):
        parent = _make_parent_mock({"sel_a": 0})
        result = await find_first_element(parent, ["sel_a"])
        assert result is None

    async def test_returns_none_for_empty_selector_list(self):
        parent = _make_parent_mock({})
        result = await find_first_element(parent, [])
        assert result is None
