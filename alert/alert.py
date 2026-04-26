"""
East Boston Street Cleaning — Daily Email Alert
Runs via GitHub Actions every morning at 7am EST.
Sends a Gmail alert listing streets being cleaned in the next 3 days.
"""

import os
import smtplib
import math
import requests
import csv
import io
from datetime import date, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

# ── Config ────────────────────────────────────────────────────────────────
RESOURCE_ID   = "9fdbdcad-67c8-4b23-b6ec-861e77d56227"
CKAN_URL      = f"https://data.boston.gov/api/3/action/resource_show?id={RESOURCE_ID}"
GMAIL_USER    = os.environ["GMAIL_USER"]
GMAIL_PASS    = os.environ["GMAIL_APP_PASSWORD"]
ALERT_EMAIL   = os.environ["ALERT_EMAIL"]
LOOKAHEAD     = 3   # days ahead to check

DAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
MONTHS_ACTIVE = range(4, 12)  # April (4) to November (11)

# Boston city holidays where daytime cleaning is suspended
# Format: (month, day)
CITY_HOLIDAYS = {
    (1, 1),   # New Year's Day
    (1, 20),  # MLK Day (approximate — 3rd Monday)
    (2, 17),  # Presidents' Day (approximate)
    (4, 21),  # Patriots' Day (3rd Monday in April)
    (5, 26),  # Memorial Day (approximate)
    (6, 19),  # Juneteenth
    (7, 4),   # Independence Day
    (9, 1),   # Labor Day (approximate)
    (10, 13), # Columbus Day (approximate)
    (11, 11), # Veterans Day
    (11, 27), # Thanksgiving (approximate)
    (12, 25), # Christmas
}


# ── Schedule logic ────────────────────────────────────────────────────────

def week_of_month(d: date) -> int:
    """Returns which week of the month (1-5) a date falls in."""
    return math.ceil(d.day / 7)


def is_season_active(d: date) -> bool:
    return d.month in MONTHS_ACTIVE


def is_holiday(d: date) -> bool:
    return (d.month, d.day) in CITY_HOLIDAYS


def is_scheduled(row: dict, d: date) -> bool:
    """Returns True if this street row is scheduled for cleaning on date d."""
    if row.get("every_day") == "t":
        return True
    day_col  = DAYS[d.weekday()]   # weekday(): 0=Mon, 6=Sun
    # CSV uses sunday-monday-...-saturday order; weekday() is 0=Mon
    # Remap: weekday 0(Mon)→monday, 6(Sun)→sunday
    day_col  = ["monday","tuesday","wednesday","thursday","friday","saturday","sunday"][d.weekday()]
    week_col = f"week_{week_of_month(d)}"
    return row.get(day_col) == "t" and row.get(week_col) == "t"


def format_time(t: str) -> str:
    if not t:
        return ""
    h, m, *_ = t.split(":")
    hour = int(h)
    ampm = "AM" if hour < 12 else "PM"
    return f"{hour % 12 or 12}:{m} {ampm}"


def week_description(row: dict) -> str:
    weeks = [str(n) for n in range(1, 6) if row.get(f"week_{n}") == "t"]
    if len(weeks) == 5:
        return "every week"
    return f"weeks {', '.join(weeks)}" if weeks else ""


# ── Data fetching ─────────────────────────────────────────────────────────

def fetch_east_boston_streets() -> list[dict]:
    """Fetches the Boston street sweeping CSV and returns East Boston rows."""
    # Step 1: get current CSV URL from CKAN (URL rotates on each update)
    meta = requests.get(CKAN_URL, timeout=15).json()
    if not meta.get("success"):
        raise RuntimeError("CKAN API returned an error")
    csv_url = meta["result"]["url"]

    # Step 2: download CSV
    resp = requests.get(csv_url, timeout=30)
    resp.raise_for_status()

    # Step 3: parse and filter to East Boston
    reader = csv.DictReader(io.StringIO(resp.text))
    return [
        row for row in reader
        if row.get("dist_name", "").strip().lower() == "east boston"
    ]


# ── Email builder ─────────────────────────────────────────────────────────

def build_email_body(schedule: dict[date, list[dict]]) -> tuple[str, str]:
    """Returns (subject, html_body) for the alert email."""
    total = sum(len(v) for v in schedule.values())
    days_with_cleaning = [d for d, rows in schedule.items() if rows]

    if total == 0:
        subject = "East Boston Street Cleaning — No cleaning in the next 3 days"
        html = f"""
        <p style="font-family:monospace;color:#555;">
          No East Boston streets are scheduled for cleaning in the next {LOOKAHEAD} days.
          No action needed. 🎉
        </p>"""
        return subject, html

    subject = f"🧹 East Boston Cleaning Alert — {total} street{'s' if total>1 else ''} in next {LOOKAHEAD} days"

    sections = []
    for d, rows in schedule.items():
        if not rows:
            continue
        day_label = d.strftime("%A, %B %-d")
        rows_sorted = sorted(rows, key=lambda r: r.get("st_name", ""))

        cards = ""
        for row in rows_sorted:
            name  = row.get("st_name", "—")
            side  = row.get("side", "")
            frm   = row.get("from", "")
            to    = row.get("to", "")
            t1    = format_time(row.get("start_time", ""))
            t2    = format_time(row.get("end_time", ""))
            freq  = week_description(row)

            side_color = "#E8782A" if side.lower() == "odd" else "#1A8C68" if side.lower() == "even" else "#4A5568"
            side_bg    = "#FDF0E6" if side.lower() == "odd" else "#E3F5EF" if side.lower() == "even" else "#EEF0F5"

            cards += f"""
            <tr>
              <td style="padding:10px 12px;border-bottom:1px solid #F0EEE8;">
                <div style="font-family:monospace;font-weight:600;font-size:14px;color:#1A1A1A;">{name}</div>
                <div style="margin-top:4px;font-size:12px;color:#6B6860;font-family:monospace;">
                  {f'📍 {frm} → {to}' if frm else ''} &nbsp;
                  {f'🕐 {t1}–{t2}' if t1 else ''}
                  {f'<br>↻ {freq}' if freq else ''}
                </div>
              </td>
              <td style="padding:10px 12px;border-bottom:1px solid #F0EEE8;vertical-align:top;text-align:right;">
                <span style="
                  font-family:monospace;font-size:11px;font-weight:600;
                  padding:3px 9px;border-radius:20px;
                  background:{side_bg};color:{side_color};">
                  {side or '—'}
                </span>
              </td>
            </tr>"""

        sections.append(f"""
        <div style="margin-bottom:28px;">
          <div style="font-family:monospace;font-size:13px;font-weight:600;
                      color:#1B2A4A;background:#F4F3EE;padding:8px 12px;
                      border-radius:6px;margin-bottom:8px;">
            📅 {day_label}
            <span style="font-weight:400;color:#6B6860;margin-left:8px;">
              {len(rows)} street{'s' if len(rows)!=1 else ''}
            </span>
          </div>
          <table width="100%" cellspacing="0" cellpadding="0"
                 style="border:1px solid #E0DED6;border-radius:8px;overflow:hidden;
                        border-collapse:collapse;background:#fff;">
            {cards}
          </table>
        </div>""")

    html = f"""
    <!DOCTYPE html>
    <html>
    <body style="margin:0;padding:0;background:#F4F3EE;font-family:'DM Sans',Arial,sans-serif;">
      <div style="max-width:600px;margin:0 auto;padding:24px 16px;">

        <!-- Header -->
        <div style="background:#1B2A4A;border-radius:10px;padding:20px 24px;margin-bottom:24px;">
          <h1 style="color:#fff;font-size:18px;margin:0;font-weight:600;">
            🧹 East Boston Street Cleaning
          </h1>
          <p style="color:rgba(255,255,255,0.55);font-size:12px;margin:4px 0 0;font-family:monospace;">
            Next {LOOKAHEAD} days · {total} street{'s' if total!=1 else ''} scheduled
          </p>
        </div>

        <!-- Schedule sections -->
        {''.join(sections)}

        <!-- Footer -->
        <div style="border-top:1px solid #E0DED6;padding-top:16px;
                    font-size:11px;color:#9B9890;font-family:monospace;text-align:center;">
          Data: City of Boston Open Data ·
          Program active April 1 – November 30 ·
          <a href="https://aboum97.github.io/East-Boston-Street-Cleaning"
             style="color:#9B9890;">View full schedule</a>
        </div>

      </div>
    </body>
    </html>"""

    return subject, html


# ── Email sending ─────────────────────────────────────────────────────────

def send_email(subject: str, html_body: str) -> None:
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = GMAIL_USER
    msg["To"]      = ALERT_EMAIL
    msg.attach(MIMEText(html_body, "html"))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(GMAIL_USER, GMAIL_PASS)
        server.sendmail(GMAIL_USER, ALERT_EMAIL, msg.as_string())
        print(f"✓ Alert sent to {ALERT_EMAIL}")


# ── Main ──────────────────────────────────────────────────────────────────

def main():
    today = date.today()

    # Check season
    if not is_season_active(today):
        print(f"Program inactive in month {today.month}. No alert sent.")
        return

    print("Fetching East Boston street data…")
    streets = fetch_east_boston_streets()
    print(f"Found {len(streets)} East Boston street segments")

    # Build schedule for next LOOKAHEAD days
    schedule: dict[date, list[dict]] = {}
    for offset in range(LOOKAHEAD):
        d = today + timedelta(days=offset)
        if is_holiday(d):
            print(f"  {d}: city holiday — skipping")
            schedule[d] = []
            continue
        scheduled = [r for r in streets if is_scheduled(r, d)]
        print(f"  {d} ({d.strftime('%A')}): {len(scheduled)} streets")
        schedule[d] = scheduled

    total = sum(len(v) for v in schedule.values())

    if total == 0:
        print("No cleaning scheduled in the next 3 days. No email sent.")
        return

    subject, html = build_email_body(schedule)
    send_email(subject, html)


if __name__ == "__main__":
    main()
