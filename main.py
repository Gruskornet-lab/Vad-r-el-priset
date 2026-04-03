"""
main.py
-------
Entry point for the Electricity Price Notifier.
 
This script is triggered by GitHub Actions on two schedules:
  1. Every evening at 21:00 CET → fetches tomorrow's prices, saves the 3
     cheapest hours to schedule.json, and sends the evening summary
  2. Every hour at xx:30 CET → reads schedule.json and sends a 30-minute
     warning if a cheap window is scheduled to start at xx+1:00
 
Why schedule.json?
------------------
Previous versions tried to calculate cheapest hours in real-time during
the hourly check. This caused repeated timezone bugs because GitHub Actions
runs in UTC but electricity prices are in CET. The root fix is simple:
decide the alert times once (at 21:00 when prices are known), save them,
and let the hourly check just read that saved decision.
 
Flow:
  21:00 CET: evening run
    → fetch tomorrow's prices
    → find 3 cheapest hours (e.g. [10, 13, 15])
    → save to schedule.json: {"date": "2026-04-02", "alert_hours_cet": [10, 13, 15]}
    → send evening summary notification
    → commit schedule.json to repo
 
  xx:30 CET each hour: check run
    → read schedule.json
    → check if date matches today
    → check if any alert_hours_cet == current CET hour + 1
    → if match → send 30-minute warning
 
Usage:
    python main.py --mode evening     # Evening summary + save schedule
    python main.py --mode check       # Read schedule and alert if needed
 
Environment variables required:
    NTFY_TOPIC    — The ntfy.sh topic name (set as GitHub Secret)
    ZONE          — Swedish price zone, default: SE3
    GITHUB_TOKEN  — Automatically provided by GitHub Actions (for committing schedule.json)
"""
 
import argparse
import json
import os
import sys
from datetime import datetime, timedelta, timezone
 
from price_fetcher import fetch_tomorrow_prices, fetch_today_prices
from price_analyzer import get_cheapest_hours, group_consecutive_hours
from notifier import send_evening_summary, send_upcoming_alert
 
 
# ── Configuration ─────────────────────────────────────────────────────────────
 
ZONE          = os.environ.get("ZONE", "SE3")
NTFY_TOPIC    = os.environ.get("NTFY_TOPIC", "")
TOP_N_HOURS   = 3
SCHEDULE_FILE = "schedule.json"
CET           = timezone(timedelta(hours=1))
 
 
# ── Schedule helpers ──────────────────────────────────────────────────────────
 
def save_schedule(date_str: str, alert_hours: list):
    """
    Save tomorrow's alert hours to schedule.json.
 
    This file is committed to the repo so the hourly-check job can read it.
    The hourly-check never recalculates — it simply reads this file.
 
    Args:
        date_str:    ISO date for tomorrow, e.g. "2026-04-02"
        alert_hours: CET hours that should trigger 30-min alerts, e.g. [10, 13, 15]
    """
    schedule = {
        "date": date_str,
        "alert_hours_cet": alert_hours,
    }
    with open(SCHEDULE_FILE, "w") as f:
        json.dump(schedule, f, indent=2)
    print(f"[Main] Schedule saved: {schedule}")
 
 
def load_schedule():
    """
    Load schedule.json from disk.
 
    Returns:
        The schedule dict, or None if file doesn't exist.
    """
    if not os.path.exists(SCHEDULE_FILE):
        print(f"[Main] No {SCHEDULE_FILE} found — evening run may not have completed yet.")
        return None
 
    with open(SCHEDULE_FILE) as f:
        schedule = json.load(f)
 
    print(f"[Main] Loaded schedule: {schedule}")
    return schedule
 
 
# ── Modes ─────────────────────────────────────────────────────────────────────
 
def run_evening_summary():
    """
    Fetch tomorrow's prices, save alert schedule, send evening summary.
    Runs every evening at 21:00 CET via GitHub Actions.
    """
    print(f"[Main] Running evening summary for zone {ZONE}...")
 
    try:
        prices = fetch_tomorrow_prices(zone=ZONE)
    except Exception as e:
        print(f"[Main] Could not fetch tomorrow's prices: {e}")
        sys.exit(1)
 
    cheapest_hours = get_cheapest_hours(prices, top_n=TOP_N_HOURS)
    cheapest_groups = group_consecutive_hours(cheapest_hours)
 
    print(f"[Main] Found {len(cheapest_groups)} cheap window(s) for tomorrow:")
    for group in cheapest_groups:
        print(f"  {group['start_hour']:02d}:00-{group['end_hour']:02d}:00 @ {group['avg_price']} SEK/kWh")
 
    # Save the start hour of each cheap window as the alert trigger times.
    # The hourly-check will send a 30-min warning before each of these hours.
    alert_hours = [group["start_hour"] for group in cheapest_groups]
    tomorrow_str = (datetime.now(tz=CET) + timedelta(days=1)).strftime("%Y-%m-%d")
    save_schedule(date_str=tomorrow_str, alert_hours=alert_hours)
 
    success = send_evening_summary(
        topic=NTFY_TOPIC,
        cheapest_groups=cheapest_groups,
        date_label="imorgon",
    )
 
    if not success:
        sys.exit(1)
 
    print("[Main] Evening summary sent successfully.")
 
 
def run_hourly_check():
    """
    Read schedule.json and send a 30-minute warning if a cheap window starts soon.
    Runs every hour at xx:30 CET via GitHub Actions (cron: 30 * * * * UTC = xx:30 CET).
 
    Key insight: this function never recalculates which hours are cheap.
    It only reads the decision already made by last night's evening run.
    This eliminates all timezone calculation bugs from previous versions.
    """
    now_cet = datetime.now(tz=CET)
    upcoming_hour = (now_cet + timedelta(minutes=30)).hour
 
    print(f"[Main] Hourly check at {now_cet.strftime('%H:%M')} CET — "
          f"looking for alert at {upcoming_hour:02d}:00 CET...")
 
    schedule = load_schedule()
    if schedule is None:
        return
 
    # Verify schedule is for today
    today_str = now_cet.strftime("%Y-%m-%d")
    if schedule["date"] != today_str:
        print(f"[Main] Schedule date {schedule['date']} does not match today {today_str} — skipping.")
        return
 
    alert_hours = schedule["alert_hours_cet"]
 
    if upcoming_hour not in alert_hours:
        print(f"[Main] {upcoming_hour:02d}:00 is not a scheduled alert hour {alert_hours} — no notification.")
        return
 
    # Match found — fetch prices to get the full group details for the notification
    print(f"[Main] Match! {upcoming_hour:02d}:00 CET is a cheap window. Fetching price details...")
 
    try:
        prices = fetch_today_prices(zone=ZONE)
    except Exception as e:
        print(f"[Main] Could not fetch today's prices: {e}")
        sys.exit(1)
 
    cheapest_hours_list = get_cheapest_hours(prices, top_n=TOP_N_HOURS)
    cheapest_groups = group_consecutive_hours(cheapest_hours_list)
 
    target_group = next(
        (g for g in cheapest_groups if g["start_hour"] == upcoming_hour),
        None
    )
 
    if target_group is None:
        print(f"[Main] Could not find price group for {upcoming_hour:02d}:00 — skipping.")
        return
 
    success = send_upcoming_alert(topic=NTFY_TOPIC, group=target_group)
    if not success:
        sys.exit(1)
 
    print("[Main] 30-minute alert sent successfully.")
 
 
# ── Entry Point ───────────────────────────────────────────────────────────────
 
if __name__ == "__main__":
    if not NTFY_TOPIC:
        print("[Main] NTFY_TOPIC environment variable is not set.")
        sys.exit(1)
 
    parser = argparse.ArgumentParser(description="Electricity Price Notifier")
    parser.add_argument(
        "--mode",
        choices=["evening", "check"],
        required=True,
        help="'evening' = fetch prices, save schedule, send summary | "
             "'check' = read schedule and alert if needed",
    )
    args = parser.parse_args()
 
    if args.mode == "evening":
        run_evening_summary()
    elif args.mode == "check":
        run_hourly
