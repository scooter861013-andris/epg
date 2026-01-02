import os
import re
import json
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from zoneinfo import ZoneInfo


# -------------------------------------------------
# KONFIG
# -------------------------------------------------
LOCATION = os.getenv("IDOKEP_LOCATION", "Hajduhadhaz")
URL = f"https://www.idokep.hu/idojaras/{LOCATION}"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (GitHubActions)"
}

# -------------------------------------------------
# LETÖLTÉS
# -------------------------------------------------
resp = requests.get(URL, headers=HEADERS, timeout=15)
resp.raise_for_status()
soup = BeautifulSoup(resp.text, "html.parser")

# -------------------------------------------------
# AKTUÁLIS HŐMÉRSÉKLET
# -------------------------------------------------
current_temp = None
temp_el = soup.select_one(".current-temperature")
if temp_el:
    try:
        current_temp = float(
            temp_el.text.replace("˚C", "").replace("°C", "").strip()
        )
    except ValueError:
        pass

# -------------------------------------------------
# AKTUÁLIS IDŐJÁRÁS
# -------------------------------------------------
current_cond = None
cond_el = soup.select_one(".current-weather")
if cond_el:
    current_cond = cond_el.text.strip()

# -------------------------------------------------
# IKON MAP
# -------------------------------------------------
ICON_MAP = {
    "napos": "☀️",
    "derült": "🌙",
    "felhős": "☁️",
    "borult": "☁️",
    "eső": "🌧️",
    "zápor": "🌧️",
    "hó": "❄️",
    "havazás": "❄️",
    "zivatar": "⛈️",
    "köd": "🌫️"
}

def condition_to_icon(text):
    if not text:
        return None
    text = text.lower()
    for k, v in ICON_MAP.items():
        if k in text:
            return v
    return None

current_icon = condition_to_icon(current_cond)

# -------------------------------------------------
# 7 NAPOS ELŐREJELZÉS  ✅ HELYES IDŐKÉP DOM
# -------------------------------------------------
forecast_7d = []

cards = soup.select(".ik.dailyForecastCol")[:7]

for card in cards:
    day = None
    tmin = None
    tmax = None
    condition = None
    icon = None

    # nap
    a_el = card.select_one(".dfIconAlert a")
    if a_el and a_el.has_attr("title"):
    title = a_el["title"]

    # pl: "Szombat<br>2026. január 3."
    parts = title.split("<br>")
    day = parts[0].strip() if parts else None


    # max
    max_el = card.select_one(".max a")
    if max_el:
        try:
            tmax = int(max_el.text.strip())
        except ValueError:
            pass

    # min
    min_el = card.select_one(".min a")
    if min_el:
        try:
            tmin = int(min_el.text.strip())
        except ValueError:
            pass

    # állapot szöveg (data-bs-content-ből)
    a_el = card.select_one(".dfIconAlert a")
    if a_el and a_el.has_attr("data-bs-content"):
        html = a_el["data-bs-content"]
        m = re.search(r"popover-icon[^>]*>\s*([^<\n\r]+)", html)
        if m:
            condition = m.group(1).strip()
            icon = condition_to_icon(condition)

    forecast_7d.append({
        "day": day,
        "min": tmin,
        "max": tmax,
        "condition": condition,
        "icon": icon
    })

# -------------------------------------------------
# JSON KIMENET
# -------------------------------------------------

old_data = None
if os.path.exists("idokep.json"):
    with open("idokep.json", "r", encoding="utf-8") as f:
        old_data = json.load(f)
now = datetime.now(ZoneInfo("Europe/Budapest")).isoformat(timespec="minutes")
data = {
    "source": "idokep.hu",
    "location": LOCATION,
    "updated": (
        old_data.get("updated")
        if old_data
        and old_data.get("current") == {
            "temperature": current_temp,
            "condition": current_cond,
            "icon": current_icon
        }
        and old_data.get("forecast_7d") == forecast_7d
        else now
    ),
    "flow_last_run": now,
    "current": {
        "temperature": current_temp,
        "condition": current_cond,
        "icon": current_icon
    },
    "forecast_7d": forecast_7d
}

with open("idokep.json", "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print("Időkép JSON frissítve (aktuális + 7 napos előrejelzés)")
