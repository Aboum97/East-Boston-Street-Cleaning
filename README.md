# 🧹 East Boston Street Cleaning Alerts

> Never get a $40 street cleaning ticket again. Get daily emails listing every East Boston street being cleaned in the next 3 days — and browse the full schedule on a live website.

[![Live Site](https://img.shields.io/badge/Live%20Site-GitHub%20Pages-blue?style=flat-square)](https://aboum97.github.io/East-Boston-Street-Cleaning)
[![Daily Alert](https://img.shields.io/badge/Alert-Gmail%20%2B%20GitHub%20Actions-red?style=flat-square)](https://github.com/Aboum97/East-Boston-Street-Cleaning/actions)
[![Data Source](https://img.shields.io/badge/Data-City%20of%20Boston%20Open%20Data-green?style=flat-square)](https://data.boston.gov/dataset/street-sweeping-schedules)
[![License](https://img.shields.io/badge/License-MIT-yellow?style=flat-square)](LICENSE)

---

## What this does

**Website** — A live filterable dashboard showing which East Boston streets are being cleaned, by day of week and odd/even side. No login, no app, just a URL.

**Daily email** — Every morning at 7am EST, a GitHub Actions job checks the next 3 days of the schedule and sends a formatted email listing every affected street with its time window, side, and intersection details.

**Zero infrastructure** — No AWS, no server, no database. GitHub Pages hosts the site for free. GitHub Actions runs the email job for free.

---

## Live site

👉 **[aboum97.github.io/East-Boston-Street-Cleaning](https://aboum97.github.io/East-Boston-Street-Cleaning)**

---

## Features

- Filterable by day of week (Mon–Sun) — defaults to today
- Odd/even side color coding on every street card
- Cleaning time window, intersection segment (from → to), and week frequency per street
- Data pre-filtered to East Boston and cached locally — updated daily via GitHub Actions
- Instant page loads (no API calls, no CORS issues)
- Daily email with 3-day lookahead, sent to Gmail via App Password
- Seasonal awareness: no alerts November 30 – April 1 when the program is inactive

---

## How it works

```
     Boston Open Data (CKAN API)
               │
               ▼
      update_data.py (8am UTC daily)
      ├─ fetches CSV (~600KB)
      ├─ filters to East Boston
      └─ saves data/east-boston.json
               │
               ├─────────────────────┐
               ▼                     ▼
          index.html             alert.py
        (GitHub Pages)      (11am UTC daily)
     Reads local JSON      Reads local JSON
       Live website         Email next 3 days
```

The schedule CSV has a row per street segment per side. Each row has boolean columns for which days of the week (`monday`, `tuesday`, ...) and which weeks of the month (`week_1` through `week_5`) cleaning occurs. A street is scheduled on a given date if its day column and week-of-month column are both `t`.

---

## Project structure

```
East-Boston-Street-Cleaning/
├── index.html                        # Website (GitHub Pages)
├── data/
│   └── east-boston.json              # Pre-filtered East Boston data (updated daily)
├── scripts/
│   └── update_data.py                # Data fetcher (filters CSV → JSON)
├── alert/
│   ├── alert.py                      # Email alert script
│   └── requirements.txt              # Python dependencies
├── .github/
│   └── workflows/
│       ├── update_data.yml           # Data update job (8am UTC daily)
│       └── daily_alert.yml           # Email alert job (11am UTC daily)
├── .gitignore
└── README.md
```

---

## Setup

### 1. Fork & enable GitHub Pages

1. Fork this repo
2. Go to **Settings → Pages**
3. Set source to `Deploy from a branch` → `main` → `/ (root)`
4. Your site is live at `https://yourusername.github.io/East-Boston-Street-Cleaning`

### 2. Set up Gmail App Password

You need a Gmail App Password so the script can send email on your behalf without using your real password.

1. Go to [myaccount.google.com/security](https://myaccount.google.com/security)
2. Make sure **2-Step Verification** is enabled
3. Search for **App Passwords**
4. Create a new app password — name it "Street Cleaning Alert"
5. Copy the 16-character password (you'll only see it once)

### 3. Add GitHub secrets

Go to your repo → **Settings → Secrets and variables → Actions → New repository secret**

Add these three secrets:

| Secret name | Value |
|---|---|
| `GMAIL_USER` | Your full Gmail address (e.g. `you@gmail.com`) |
| `GMAIL_APP_PASSWORD` | The 16-character app password from step 2 |
| `ALERT_EMAIL` | Email address to send alerts to (can be same as above) |

### 4. Test the alert

Go to **Actions → Daily Street Cleaning Alert → Run workflow** to trigger it manually and confirm you receive an email.

---

## Local development

```bash
# Clone the repo
git clone https://github.com/Aboum97/East-Boston-Street-Cleaning.git
cd East-Boston-Street-Cleaning

# Run the website locally (any static server works)
python3 -m http.server 8080
# Open http://localhost:8080

# Set up Python environment for the alert script
cd alert
pip install -r requirements.txt

# Test the alert script locally
export GMAIL_USER="you@gmail.com"
export GMAIL_APP_PASSWORD="your-app-password"
export ALERT_EMAIL="you@gmail.com"
python alert.py
```

---

## Schedule logic

Boston's street cleaning program runs **April 1 – November 30**. Each street segment has:

- **Day columns** (`monday`, `tuesday`, etc.) — which days of the week it's cleaned
- **Week columns** (`week_1` through `week_5`) — which weeks of the month
- **Side** (`Odd` / `Even`) — which side of the street the restriction applies to

A street is scheduled on a given date if **both** its day column and its week-of-month column are `t`.

The week-of-month is computed as: `week = ceil(day_of_month / 7)`.

Streets marked `every_day = t` are cleaned every single day (typically Downtown overnight cleaning — not common in East Boston).

---

## Data source

City of Boston Open Data — Street Sweeping Schedules  
[data.boston.gov/dataset/street-sweeping-schedules](https://data.boston.gov/dataset/street-sweeping-schedules)  
License: Open Data Commons Public Domain Dedication and License (PDDL)  
Last updated: daily

---

## Contributing

Pull requests welcome. To add a feature:

1. Fork the repo
2. Create a branch: `git checkout -b feature/my-feature`
3. Make your changes
4. Open a pull request

For bugs or ideas, open an [issue](https://github.com/Aboum97/East-Boston-Street-Cleaning/issues).

---

## License

MIT — do whatever you want with it.
