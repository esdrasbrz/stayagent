"""
Centralized Selector Registry for platform crawlers.

Maps semantic field names to ordered lists of CSS selectors per platform.
Selectors are tried in order (Primary -> Backup -> Legacy) to provide
graceful degradation when platforms update their UI.
"""

from typing import List

SELECTORS: dict[str, dict[str, list[str]]] = {
    "airbnb": {
        "LISTING_CONTAINER": [
            'div[itemprop="itemListElement"]',
            'div[data-testid="card-container"]',
        ],
        "TITLE": [
            'div[data-testid="listing-card-title"]',
            'meta[itemprop="name"]',
        ],
        "PRICE": [
            'span:has-text("$"), span:has-text("€"), span:has-text("£"), span:has-text("R$")',
        ],
        "LINK": ["a"],
        "IMAGE": ["img"],
    },
    "booking": {
        "LISTING_CONTAINER": [
            'div[data-testid="property-card"]',
            "div.sr_property_block",
        ],
        "TITLE": [
            'div[data-testid="title"]',
        ],
        "TITLE_LINK": [
            'a[data-testid="title-link"]',
            "a.e13098a59f",
        ],
        "PRICE": [
            'span[data-testid="price-and-discounted-price"]',
        ],
        "RATING": [
            'div[data-testid="review-score"] > div',
        ],
        "IMAGE": [
            'img[data-testid="image"]',
        ],
        "COOKIE_BANNER": [
            "button#onetrust-accept-btn-handler",
        ],
    },
}


def get_selectors(platform: str, field: str) -> List[str]:
    """
    Retrieve the ordered list of selectors for a given platform and field.

    Args:
        platform: Platform key (e.g., "airbnb", "booking").
        field: Semantic field key (e.g., "LISTING_CONTAINER", "TITLE").

    Returns:
        List of CSS selector strings, ordered by priority.

    Raises:
        KeyError: If the platform or field is not registered.
    """
    try:
        return SELECTORS[platform][field]
    except KeyError:
        raise KeyError(
            f"No selectors registered for platform='{platform}', field='{field}'"
        )
