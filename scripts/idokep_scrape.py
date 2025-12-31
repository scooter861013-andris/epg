import os
import json
import requests
from bs4 import BeautifulSoup
from datetime import datetime

# ---- KONFIG ----
LOCATION = os.getenv("IDOKEP_LOCATION", "Hajduhadhaz")
URL = f"https://www.idokep.hu/elorejelzes/{LOCATION}"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (GitHubActions)"
}

# ---- SEGÉD ----
def clean_text(t):
    return t.replace("\xa0", " ").strip()

# ---- LETÖLTÉS ----
resp = requests.get(URL, headers=HEADERS, timeout=15)
resp.raise_for_status()

soup = BeautifulSoup(resp.text, "html.parser")

# ---- AKTUÁLIS IDŐJÁRÁS ----
current_temp = None
current_cond = None
current_icon = None

now_box = soup.select_one(".ik.current-weather")
if now_box:
    temp_el = now_box.select_one(".temp")
    cond_el = now_box.select_one(".phrase")

    if temp_el:
        current_temp = clean_text(temp_el.text).replace("°", "")
    if cond_el:
        current_cond = clean_text(cond_el.text)

# ---- IKON MAP (saját, stabil) ----
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

if current_cond:
    lc = current_cond.lower()
    for k, v in ICON_MAP.items():
        if k in lc:
            current_icon = v
            break

# ---- 7 NAPOS ELŐREJELZÉS ----
forecast = []

days = soup.select(".dailyForecast li")
for d in days[:7]:
    day_name = d.select_one(".day")
    minmax = d.select_one(".minmax")
    phrase = d.select_one(".phrase")

    if not (day_name and minmax):
        continue

    temps = clean_text(minmax.text).replace("°", "").split("/")
    if len(temps) != 2:
        continue

    icon = None
    cond = clean_text(phrase.text) if phrase else ""

    lc = cond.lower()
    for k, v in ICON_MAP.items():
        if k in lc:
            icon = v
            break

    forecast.append({
        "day": clean_text(day_name.text),
        "min": temps[0].strip(),
        "max": temps[1].strip(),
        "condition": cond,
        "icon": icon
    })

# ---- JSON ÖSSZEÁLLÍTÁS ----
data = {
    "source": "idokep.hu",
    "location": LOCATION,
    "updated": datetime.now().isoformat(timespec="minutes"),
    "current": {
        "temperature": current_temp,
        "condition": current_cond,
        "icon": current_icon
    },
    "forecast_7d": forecast
}

# ---- MENTÉS ----
with open("idokep.json", "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print("Időkép JSON frissítve")
