import re
from typing import Tuple, Optional

# Mapping commonly used symbols to 3-letter currency codes
CURRENCY_MAP = {
    "$": "USD",
    "€": "EUR",
    "£": "GBP",
    "R$": "BRL",
    "A$": "AUD",
    "C$": "CAD",
    "CHF": "CHF",
    "¥": "JPY",
    "kr": "SEK",  # Could also be NOK/DKK depending on locale, but SEK is a common fallback
    "zł": "PLN",
}


def parse_price_and_currency(text: str) -> Tuple[Optional[float], str]:
    """
    Extracts the numeric price and the normalized currency code from a string.
    Example: 'R$ 1.200,50' -> (1200.5, 'BRL')
             '€123' -> (123.0, 'EUR')
             '150 kr' -> (150.0, 'SEK')
    """
    if not text:
        return None, "USD"

    # 1. Clean up characters that aren't digits, dots, commas, or currency symbols/letters
    # We keep letters and symbols to find the currency.

    # 2. Extract digits and decimals first
    # This regex looks for patterns like 1,200.50 or 1.200,50
    # We strip out the thousands separator and convert the decimal separator to a dot.

    # Remove whitespace
    clean_text = text.replace("\xa0", " ").strip()

    # Find the numeric part
    # Matches: 1,234.56 or 1.234,56 or 1234
    price_match = re.search(r"[\d.,]+", clean_text)
    if not price_match:
        return None, "USD"

    price_str = price_match.group()

    # Heuristic for thousands/decimal separator:
    # If there's both a '.' and a ',', the last one is the decimal separator.
    # If there's only one, and it's followed by 3 digits, it's likely a thousands separator.
    # Otherwise, it might be a decimal separator.

    processed_price = price_str
    if "." in price_str and "," in price_str:
        if price_str.find(".") < price_str.find(","):
            # 1.234,56 -> 1234.56
            processed_price = price_str.replace(".", "").replace(",", ".")
        else:
            # 1,234.56 -> 1234.56
            processed_price = price_str.replace(",", "")
    elif "," in price_str:
        # Check if it looks like a decimal (e.g., ,50) or thousands (e.g., 1,500)
        parts = price_str.split(",")
        if len(parts[-1]) == 3:
            processed_price = price_str.replace(",", "")
        else:
            processed_price = price_str.replace(",", ".")
    elif "." in price_str:
        parts = price_str.split(".")
        if len(parts[-1]) == 3:
            processed_price = price_str.replace(".", "")

    try:
        price_val = float(processed_price)
    except ValueError:
        price_val = None

    # 3. Extract currency
    # Remove the numeric part and clean up what remains
    remaining = clean_text.replace(price_str, "").strip()

    # If remaining contains mixed text, try to find a known symbol/code
    # This regex looks for 1-3 non-digit characters that might be a currency
    # or a 3-letter uppercase code.
    symbol_match = re.search(r"[\$€£¥]|R\$|A\$|C\$|CHF|kr|zł|[A-Z]{3}", clean_text)
    if symbol_match:
        remaining = symbol_match.group()
    elif not remaining:
        remaining = "USD"

    # Normalize
    currency_code = CURRENCY_MAP.get(remaining, remaining)

    return price_val, currency_code
