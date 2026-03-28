"""
price_analyzer.py
-----------------
Analyzes hourly electricity prices to identify the cheapest hours of the day.

Strategy:
- Rank all 24 hours by price (ascending)
- Select the top N cheapest hours (default: 3)
- Group consecutive hours into time windows for cleaner notifications
  e.g. hours 13, 14, 15 become "13:00–16:00" instead of three separate entries
"""


def get_cheapest_hours(prices: list[dict], top_n: int = 3) -> list[dict]:
    """
    Return the N cheapest hours from a full day of hourly prices.

    Args:
        prices: List of hourly price dicts from price_fetcher.py
        top_n: Number of cheapest hours to return (default: 3)

    Returns:
        List of the cheapest hour dicts, sorted by time (ascending hour)
    """
    sorted_by_price = sorted(prices, key=lambda x: x["price_sek"])
    cheapest = sorted_by_price[:top_n]

    # Return sorted by hour so notifications appear in chronological order
    cheapest.sort(key=lambda x: x["hour"])
    return cheapest


def group_consecutive_hours(hours: list[dict]) -> list[dict]:
    """
    Merge consecutive hours into time windows.

    Example:
        Input:  [hour=13, hour=14, hour=15]
        Output: [{"start_hour": 13, "end_hour": 16, "avg_price": ...}]

    Args:
        hours: List of hourly price dicts, sorted by hour

    Returns:
        List of grouped windows with start_hour, end_hour, avg_price, min_price
    """
    if not hours:
        return []

    groups = []
    current_group = [hours[0]]

    for entry in hours[1:]:
        prev_hour = current_group[-1]["hour"]
        if entry["hour"] == prev_hour + 1:
            # Consecutive — extend current group
            current_group.append(entry)
        else:
            # Gap found — save current group and start a new one
            groups.append(_build_group(current_group))
            current_group = [entry]

    # Save the last group
    groups.append(_build_group(current_group))

    return groups


def _build_group(hours: list[dict]) -> dict:
    """
    Build a summary dict for a group of consecutive hours.

    Args:
        hours: List of consecutive hourly price dicts

    Returns:
        Dict with start_hour, end_hour, avg_price, min_price, hours
    """
    prices = [h["price_sek"] for h in hours]
    start = hours[0]["hour"]
    end = hours[-1]["hour"] + 1  # end is exclusive (e.g. hour 13 ends at 14:00)

    return {
        "start_hour": start,
        "end_hour": end,
        "avg_price": round(sum(prices) / len(prices), 4),
        "min_price": round(min(prices), 4),
        "hours": hours,
    }


def format_time_range(group: dict) -> str:
    """
    Format a group's time range as a human-readable string.

    Example: {"start_hour": 13, "end_hour": 16} → "13:00–16:00"
    """
    return f"{group['start_hour']:02d}:00–{group['end_hour']:02d}:00"


def format_price(price_sek: float) -> str:
    """
    Format a price as a human-readable string in öre/kWh.
    Using öre (1 SEK = 100 öre) is more intuitive for small electricity prices.

    Example: 0.4523 → "45.2 öre/kWh"
    """
    ore = price_sek * 100
    return f"{ore:.1f} öre/kWh"
