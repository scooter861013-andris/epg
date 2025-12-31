import os
import json
import requests
from bs4 import BeautifulSoup
from datetime import datetime

LOCATION = os.getenv("IDOKEP_LOCATION", "Hajduhadhaz")
URL = f"https://www.idokep.hu/idojaras/{LOCATION}"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (GitHubActions)"
}

resp = requests.get(URL, headers=HEADERS, timeout=15)
resp.raise_for_status()

soup = BeautifulSoup(resp.text, "html.parser")

# ---- AKTUÁLIS HŐMÉRSÉKLET ----
current_temp = None
temp_el = soup.select_one(".current-temperature")
if temp_el:
    try:
        current_temp = float(
            temp_el.text.replace("˚C", "").replace("°C", "").strip()
        )
    except ValueError:
        pass

# ---- AKTUÁLIS IDŐJÁRÁS ----
current_cond = None
cond_el = soup.select_one(".current-weather")
if cond_el:
    current_cond = cond_el.text.strip()

# ---- IKON MAP ----
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
    lc = text.lower()
    for k, v in ICON_MAP.items():
        if k in lc:
            return v
    return None

current_icon = condition_to_icon(current_cond)

# ---- 7 NAPOS ELŐREJELZÉS ----
forecast_7d = []

cards = soup.select(".dailyForecast .dfItem")[:7]

for card in cards:
    day_name = None
    tmin = tmax = None
    condition = None
    icon = None

    day_el = card.select_one(".dfDay")
    if day_el:
        day_name = day_el.text.strip()

    min_el = card.select_one(".dfMin")
    if min_el:
        try:
            tmin = int(min_el.text.replace("°", "").strip())
        except ValueError:
            pass

    max_el = card.select_one(".dfMax")
    if max_el:
        try:
            tmax = int(max_el.text.replace("°", "").strip())
        except ValueError:
            pass

    img_el = card.select_one("img")
    if img_el and img_el.get("alt"):
        condition = img_el["alt"].strip()
        icon = condition_to_icon(condition)

    forecast_7d.append({
        "day": day_name,
        "min": tmin,
        "max": tmax,
        "condition": condition,
        "icon": icon
    })

# ---- JSON KIMENET ----
data = {
    "source": "idokep.hu",
    "location": LOCATION,
    "updated": datetime.now().isoformat(timespec="minutes"),
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
