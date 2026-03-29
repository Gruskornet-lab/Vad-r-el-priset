"""
main.py
-------
Entry point for the Electricity Price Notifier.
 
This script is triggered by GitHub Actions on two schedules:
  1. Every evening at 21:00 CET → sends tomorrow's cheapest hours summary
  2. Every hour (xx:30) → checks if a cheap window starts in 30 minutes,
     and sends an alert if so
 
Usage:
    python main.py --mode evening     # Send evening summary for tomorrow
    python main.py --mode check       # Check if alert needed right now
 
Environment variables required:
    NTFY_TOPIC   — The ntfy.sh topic name (set as GitHub Secret)
    ZONE         — Swedish price zone, default: SE3
"""
 
import argparse
import os
import sys
from datetime import datetime, timedelta, timezone, time as dt_time
 
from price_fetcher import fetch_tomorrow_prices, fetch_today_prices
from price_analyzer import get_cheapest_hours, group_consecutive_hours
from notifier import send_evening_summary, send_upcoming_alert
 
 
# ── Configuration ────────────────────────────────────────────────────────────
 
ZONE = os.environ.get("ZONE", "SE3")
NTFY_TOPIC = os.environ.get("NTFY_TOPIC", "")
TOP_N_HOURS = 3  # Max notifications per day
 
 
# ── Modes ────────────────────────────────────────────────────────────────────
 
def run_evening_summary():
    """
    Fetch tomorrow's prices and send a summary of the 3 cheapest windows.
    Runs every evening at 21:00 CET via GitHub Actions.
    """
    print(f"[Main] Running evening summary for zone {ZONE}...")
 
    try:
        prices = fetch_tomorrow_prices(zone=ZONE)
    except Exception as e:
        print(f"[Main] ❌ Could not fetch tomorrow's prices: {e}")
        print("[Main] Tomorrow's prices may not be published yet (published ~13:00 CET).")
        sys.exit(1)
 
    cheapest_hours = get_cheapest_hours(prices, top_n=TOP_N_HOURS)
    cheapest_groups = group_consecutive_hours(cheapest_hours)
 
    print(f"[Main] Found {len(cheapest_groups)} cheap window(s) for tomorrow:")
    for group in cheapest_groups:
        print(f"  • {group['start_hour']:02d}:00–{group['end_hour']:02d}:00 @ {group['avg_price']} SEK/kWh")
 
    success = send_evening_summary(
        topic=NTFY_TOPIC,
        cheapest_groups=cheapest_groups,
        date_label="imorgon",
    )
 
    if not success:
        sys.exit(1)
 
    print("[Main] ✅ Evening summary sent.")
 
 
def run_hourly_check():
    """
    Check if any cheap electricity window starts in approximately 30 minutes.
    Runs every hour at xx:30 via GitHub Actions.
 
    Logic:
    - Fetch today's prices
    - Find the 3 cheapest hours
    - If any of them starts in 30 minutes (i.e. current time is xx:30 and
      the cheap hour is xx+1:00), send an alert
    """
    # Use Swedish time (CET = UTC+1, CEST = UTC+2 in summer)
    # GitHub Actions runs in UTC — without this fix, hour comparisons
    # against the API's Swedish-time prices would be off by 1-2 hours
    cet = timezone(timedelta(hours=1))
    now = datetime.now(tz=cet)
    print(f"[Main] Running hourly check at {now.strftime('%H:%M')} CET for zone {ZONE}...")
 
    try:
        prices = fetch_today_prices(zone=ZONE)
    except Exception as e:
        print(f"[Main] ❌ Could not fetch today's prices: {e}")
        sys.exit(1)
 
    cheapest_hours = get_cheapest_hours(prices, top_n=TOP_N_HOURS)
    cheapest_groups = group_consecutive_hours(cheapest_hours)
 
    # The hour that starts in 30 minutes
    upcoming_hour = (now + timedelta(minutes=30)).hour
 
    # Check each cheap group — alert if it starts in ~30 min
    alert_sent = False
    for group in cheapest_groups:
        if group["start_hour"] == upcoming_hour:
            print(f"[Main] ⚡ Cheap window starting soon: {group['start_hour']:02d}:00–{group['end_hour']:02d}:00")
            success = send_upcoming_alert(topic=NTFY_TOPIC, group=group)
            if success:
                alert_sent = True
            break
 
    if not alert_sent:
        print(f"[Main] No cheap window starting at {upcoming_hour:02d}:00 — no alert needed.")
 
    print("[Main] ✅ Hourly check complete.")
 
 
# ── Entry Point ───────────────────────────────────────────────────────────────
 
if __name__ == "__main__":
    if not NTFY_TOPIC:
        print("[Main] ❌ NTFY_TOPIC environment variable is not set.")
        sys.exit(1)
 
    parser = argparse.ArgumentParser(description="Electricity Price Notifier")
    parser.add_argument(
        "--mode",
        choices=["evening", "check"],
        required=True,
        help="'evening' = send summary for tomorrow | 'check' = alert if cheap hour starts in 30 min",
    )
    args = parser.parse_args()
 
    if args.mode == "evening":
        run_evening_summary()
    elif args.mode == "check":
        run_hourly_check()
 
