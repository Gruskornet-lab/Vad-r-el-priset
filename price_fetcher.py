"""
price_fetcher.py
----------------
Fetches hourly electricity spot prices for a Swedish price zone
from the public API at https://www.elprisetjustnu.se

No API key required. Data is updated daily by the provider.

Supported zones: SE1, SE2, SE3, SE4
"""

import requests
from datetime import datetime, timedelta


# Base URL for the Elpriset Just Nu API
API_BASE = "https://www.elprisetjustnu.se/api/v1/prices"


def fetch_prices(zone: str, date: datetime) -> list[dict]:
    """
    Fetch hourly electricity prices for a given zone and date.

    Args:
        zone: Swedish price zone, e.g. "SE3"
        date: The date to fetch prices for

    Returns:
        A list of dicts, each containing:
            - hour (int): Hour of the day (0-23)
            - price_sek (float): Price in SEK per kWh (incl. VAT estimate)
            - time_start (str): ISO timestamp for start of hour
            - time_end (str): ISO timestamp for end of hour

    Raises:
        Exception: If the API request fails or returns unexpected data
    """
    year = date.strftime("%Y")
    month = date.strftime("%m")
    day = date.strftime("%d")

    url = f"{API_BASE}/{year}/{month}-{day}_{zone}.json"

    response = requests.get(url, timeout=10)

    if response.status_code == 404:
        raise Exception(f"No price data available for {zone} on {date.strftime('%Y-%m-%d')}")

    if response.status_code != 200:
        raise Exception(f"API error {response.status_code} for URL: {url}")

    raw_data = response.json()

    prices = []
    for entry in raw_data:
        # API returns price in SEK per MWh — convert to SEK per kWh
        price_kwh = entry["SEK_per_kWh"]

        time_start = entry["time_start"]
        hour = datetime.fromisoformat(time_start).hour

        prices.append({
            "hour": hour,
            "price_sek": round(price_kwh, 4),
            "time_start": time_start,
            "time_end": entry["time_end"],
        })

    # Sort by hour to ensure correct order
    prices.sort(key=lambda x: x["hour"])

    return prices


def fetch_today_prices(zone: str = "SE3") -> list[dict]:
    """Fetch electricity prices for today."""
    return fetch_prices(zone, datetime.now())


def fetch_tomorrow_prices(zone: str = "SE3") -> list[dict]:
    """
    Fetch electricity prices for tomorrow.
    Note: Tomorrow's prices are published daily around 13:00 CET by Nord Pool.
    If called before that time, this may raise an exception.
    """
    tomorrow = datetime.now() + timedelta(days=1)
    return fetch_prices(zone, tomorrow)
