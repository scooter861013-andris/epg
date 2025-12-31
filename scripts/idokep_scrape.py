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

# ---- IDŐJÁRÁS LEÍRÁS ----
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

icon = None
if current_cond:
    lc = current_cond.lower()
    for k, v in ICON_MAP.items():
        if k in lc:
            icon = v
            break

# ---- JSON ----
data = {
    "source": "idokep.hu",
    "location": LOCATION,
    "updated": datetime.now().isoformat(timespec="minutes"),
    "current": {
        "temperature": current_temp,
        "condition": current_cond,
        "icon": icon
    },
    "forecast_7d": []  # később bővíthető
}

with open("idokep.json", "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print("Időkép JSON frissítve (DOM scraping)")
