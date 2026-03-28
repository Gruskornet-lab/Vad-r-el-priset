# ⚡ Electricity Price Notifier

A fully automated push notification system that tracks Swedish electricity spot prices and alerts recipients when cheap electricity windows are approaching — helping households shift energy-intensive tasks (dishwasher, EV charging, laundry) to low-cost hours.

Built as part of a personal AI & automation learning portfolio.

---

## 📋 Table of Contents

- [What It Does](#what-it-does)
- [Architecture](#architecture)
- [Project Structure](#project-structure)
- [Setup Guide](#setup-guide)
- [How Notifications Look](#how-notifications-look)
- [Design Decisions](#design-decisions)
- [Technologies Used](#technologies-used)

---

## What It Does

The system runs automatically via GitHub Actions and:

1. **Every evening at 21:00 CET** — Fetches tomorrow's hourly electricity prices and sends a summary of the 3 cheapest time windows
2. **Every hour at :30** — Checks if a cheap electricity window starts in 30 minutes, and sends an alert if so (max 3 alerts per day)

---

## Architecture

```
GitHub Actions (scheduled)
       │
       ▼
  main.py (entry point)
       │
       ├── price_fetcher.py  ── Elpriset Just Nu API (free, no key needed)
       │                        https://www.elprisetjustnu.se/elpris-api
       │
       ├── price_analyzer.py ── Finds 3 cheapest hours, groups consecutive hours
       │
       └── notifier.py       ── Sends push via ntfy.sh
                                 Recipients use the free "ntfy" app on iOS/Android
```

**Data flow:**
```
Nord Pool spot prices → Elpriset Just Nu API → price_fetcher.py
                                                     │
                                              price_analyzer.py
                                                     │
                                               notifier.py
                                                     │
                                              ntfy.sh server
                                                     │
                                         📱 ntfy app on phone
```

---

## Project Structure

```
electricity-notifier/
├── .github/
│   └── workflows/
│       └── notify.yml        # GitHub Actions schedule and job definitions
├── src/
│   ├── price_fetcher.py      # Fetches hourly prices from Elpriset Just Nu API
│   ├── price_analyzer.py     # Identifies and groups cheapest hours
│   ├── notifier.py           # Sends push notifications via ntfy.sh
│   └── main.py               # Orchestrates all components, CLI entry point
├── requirements.txt           # Python dependencies (only: requests)
└── README.md
```

---

## Setup Guide

### Step 1 — Create a GitHub Repository

1. Go to [github.com](https://github.com) and create a new **private** repository named `electricity-notifier`
2. Upload all project files maintaining the folder structure above

### Step 2 — Choose a Secret Topic Name

The ntfy topic is a shared secret — anyone who knows it can receive (and send) messages.

Choose something unguessable, for example: `familjen-el-k7x9p2`

Avoid: `family-electricity`, `home-alerts`, or any obvious name.

### Step 3 — Add GitHub Secret

1. Go to your repository → **Settings** → **Secrets and variables** → **Actions**
2. Click **New repository secret**
3. Add:

| Name | Value |
|------|-------|
| `NTFY_TOPIC` | Your chosen topic name, e.g. `familjen-el-k7x9p2` |

### Step 4 — Install the ntfy App

Recipients need to install the **ntfy** app by **Philipp Heckel**:

- **iOS App Store:** Search for `ntfy` by Philipp Heckel
  - Direct link: https://apps.apple.com/us/app/ntfy/id1625396347
- **Android Google Play:** Search for `ntfy` by Philipp Heckel

### Step 5 — Subscribe to the Topic

In the ntfy app:
1. Tap the **+** button
2. Enter your topic name (e.g. `familjen-el-k7x9p2`)
3. Tap **Subscribe**

Done! Notifications will arrive automatically.

### Step 6 — Test Manually

In your GitHub repository:
1. Go to **Actions** tab
2. Select **Electricity Price Notifier**
3. Click **Run workflow**
4. Choose mode: `check` or `evening`
5. Click **Run workflow**

---

## How Notifications Look

### Evening Summary (21:00 CET)
```
⚡ Billig el imorgon!
Passa på att köra diskmaskinen eller laddaren under:

• 02:00–03:00  (45.2 öre/kWh)
• 13:00–14:00  (61.3 öre/kWh)
• 15:00–16:00  (63.0 öre/kWh)
```

### 30-Minute Alert
```
⚡ Billig el om 30 minuter!
Kl. 13:00–14:00 kostar elen 61.3 öre/kWh
Passa på att starta diskmaskinen! 🫧
```

---

## Design Decisions

| Decision | Reason |
|----------|--------|
| **Elpriset Just Nu API** | Free, no API key required, reliable Swedish source based on Nord Pool data |
| **ntfy.sh** | Free, open-source, no account needed, works on iOS and Android, simple HTTP API |
| **GitHub Actions** | Free for public repos, no server needed, same approach as other projects in portfolio |
| **Max 3 alerts per day** | Prevents notification fatigue — only the 3 absolute cheapest hours trigger alerts |
| **öre/kWh display** | More intuitive than SEK/kWh for Swedish electricity consumers |
| **Consecutive hour grouping** | Cleaner UX — "13:00–15:00" is easier to act on than two separate 1-hour alerts |

---

## Technologies Used

| Technology | Purpose |
|------------|---------|
| Python 3.11 | Main programming language |
| `requests` | HTTP calls to Elpriset API and ntfy.sh |
| GitHub Actions | Scheduled automation (cron jobs) |
| Elpriset Just Nu API | Swedish electricity spot prices (SE3 zone) |
| ntfy.sh | Push notification delivery |
| ntfy app (iOS/Android) | Receiving push notifications on phone |

---

## Data Source

Electricity prices are fetched from **Elpriset Just Nu** ([elprisetjustnu.se](https://www.elprisetjustnu.se)), which provides Nord Pool spot prices for all Swedish price zones via a free public API. Prices are in SEK per kWh excluding household electricity tax and distribution fees.

---

*Part of a personal AI & automation learning portfolio.*
