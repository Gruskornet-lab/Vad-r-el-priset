"""
notifier.py
-----------
Sends push notifications via ntfy.sh — a free, open-source push notification
service. No account required. Recipients subscribe to a shared topic in the
ntfy app on their phones.

Documentation: https://docs.ntfy.sh/publish/

How it works:
- We publish a message via HTTP POST to https://ntfy.sh/{TOPIC}
- Anyone subscribed to that topic in the ntfy app receives the push notification
- The topic name acts as a shared secret — keep it unguessable
"""

import os
import requests


# ntfy.sh public server — no account or API key needed
NTFY_BASE_URL = "https://ntfy.sh"


def send_notification(
    topic: str,
    title: str,
    message: str,
    priority: str = "default",
    tags: list[str] = None,
) -> bool:
    """
    Send a push notification to all subscribers of a given ntfy topic.

    Args:
        topic:    The ntfy topic name (kept secret, acts as a shared key)
        title:    Bold title shown in the notification
        message:  Body text of the notification
        priority: One of "min", "low", "default", "high", "urgent"
        tags:     Optional list of emoji tag names (e.g. ["zap", "electric_plug"])
                  See full list: https://docs.ntfy.sh/emojis/

    Returns:
        True if the notification was sent successfully, False otherwise
    """
    url = f"{NTFY_BASE_URL}/{topic}"

    headers = {
        "Title": title,
        "Priority": priority,
        "Content-Type": "text/plain; charset=utf-8",
    }

    if tags:
        headers["Tags"] = ",".join(tags)

    try:
        response = requests.post(url, data=message.encode("utf-8"), headers=headers, timeout=10)
        if response.status_code == 200:
            print(f"[Notifier] ✅ Notification sent to topic '{topic}': {title}")
            return True
        else:
            print(f"[Notifier] ❌ Failed to send notification. Status: {response.status_code}")
            return False
    except requests.RequestException as e:
        print(f"[Notifier] ❌ Request error: {e}")
        return False


def send_evening_summary(topic: str, cheapest_groups: list[dict], date_label: str = "imorgon") -> bool:
    """
    Send the evening summary notification listing tomorrow's cheapest hours.

    Args:
        topic:          ntfy topic name
        cheapest_groups: Grouped cheap hours from price_analyzer.py
        date_label:     Human-readable date label, default "imorgon"

    Returns:
        True if sent successfully
    """
    from price_analyzer import format_time_range, format_price

    lines = [f"Passa på att köra diskmaskinen eller laddaren under:\n"]
    for group in cheapest_groups:
        time_range = format_time_range(group)
        price = format_price(group["avg_price"])
        lines.append(f"• {time_range}  ({price})")

    message = "\n".join(lines)

    return send_notification(
        topic=topic,
        title=f"⚡ Billig el {date_label}!",
        message=message,
        priority="default",
        tags=["zap", "bulb"],
    )


def send_upcoming_alert(topic: str, group: dict) -> bool:
    """
    Send a 30-minute warning notification before a cheap electricity window starts.

    Args:
        topic: ntfy topic name
        group: A single grouped window from price_analyzer.py

    Returns:
        True if sent successfully
    """
    from price_analyzer import format_time_range, format_price

    time_range = format_time_range(group)
    price = format_price(group["avg_price"])

    message = (
        f"Kl. {time_range} kostar elen {price}\n"
        f"Passa på att starta diskmaskinen! 🫧"
    )

    return send_notification(
        topic=topic,
        title="⚡ Billig el om 30 minuter!",
        message=message,
        priority="high",
        tags=["zap", "alarm_clock"],
    )
