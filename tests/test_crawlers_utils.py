import pytest
from app.crawlers.utils import parse_price_and_currency

@pytest.mark.parametrize("input_text, expected_output", [
    ("$123", (123.0, "USD")),
    ("€ 145", (145.0, "EUR")),
    ("£1,200", (1200.0, "GBP")),
    ("R$ 1.500,50", (1500.5, "BRL")),
    ("150 kr", (150.0, "SEK")),
    ("A$ 99.99", (99.99, "AUD")),
    ("CHF 200", (200.0, "CHF")),
    ("Total: $500", (500.0, "USD")),
    ("", (None, "USD")),
    (None, (None, "USD")),
    ("Price: 123.45 EUR", (123.45, "EUR")),
    ("1.000,00zł", (1000.0, "PLN")),
])
def test_parse_price_and_currency(input_text, expected_output):
    assert parse_price_and_currency(input_text) == expected_output

def test_parse_price_and_currency_invalid():
    # Should handle text without numbers gracefully
    assert parse_price_and_currency("No price here")[0] is None
