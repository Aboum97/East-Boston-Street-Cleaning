"""
Fetches the Boston street sweeping CSV from the City's open data portal
and saves East Boston streets as data/east-boston.json.

Run by GitHub Actions daily — output is committed to the repo so the
website can read it locally (no CORS issues, instant page loads).
"""

import csv
import io
import json
import os
import requests
from datetime import date

RESOURCE_ID = "9fdbdcad-67c8-4b23-b6ec-861e77d56227"
CKAN_URL    = f"https://data.boston.gov/api/3/action/resource_show?id={RESOURCE_ID}"
OUTPUT_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "east-boston.json")

# Columns to keep (drop internal metadata columns)
KEEP_COLS = [
    "main_id", "st_name", "dist", "dist_name",
    "start_time", "end_time", "side", "from", "to", "miles",
    "one_way", "every_day", "year_round",
    "week_1", "week_2", "week_3", "week_4", "week_5",
    "sunday", "monday", "tuesday", "wednesday", "thursday", "friday", "saturday",
]


def main():
    print("Fetching data from Boston Open Data…")

    # Step 1: get current CSV URL (rotates on each dataset update)
    meta = requests.get(CKAN_URL, timeout=15).json()
    if not meta.get("success"):
        raise RuntimeError("CKAN API returned an error")
    csv_url      = meta["result"]["url"]
    last_modified = meta["result"].get("last_modified", "")[:10]
    print(f"CSV URL: {csv_url}")

    # Step 2: download CSV
    resp = requests.get(csv_url, timeout=30)
    resp.raise_for_status()

    # Step 3: parse + filter to East Boston
    reader = csv.DictReader(io.StringIO(resp.text))
    streets = []
    for row in reader:
        if row.get("dist_name", "").strip().lower() != "east boston":
            continue
        # Keep only needed columns
        streets.append({k: row.get(k, "") for k in KEEP_COLS if k in row})

    print(f"Found {len(streets)} East Boston street segments")

    # Step 4: write JSON
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    output = {
        "updated": last_modified or str(date.today()),
        "source":  "City of Boston Open Data — Street Sweeping Schedules",
        "count":   len(streets),
        "streets": streets,
    }
    with open(OUTPUT_PATH, "w") as f:
        json.dump(output, f, separators=(",", ":"))

    print(f"Saved {len(streets)} streets → {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
