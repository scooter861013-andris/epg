import os
import json
import requests
from bs4 import BeautifulSoup
from datetime import datetime

LOCATION = os.getenv("IDOKEP_LOCATION", "Hajduhadhaz")
URL = f"https://www.idokep.hu/elorejelzes/{LOCATION}"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (GitHubActions)"
}

resp = requests.get(URL, headers=HEADERS, timeout=15)
resp.raise_for_status()

soup = BeautifulSoup(resp.text, "html.parser")

# ---- JSON-LD KINYERÉS ----
json_ld = None
for script in soup.find_all("script", type="application/ld+json"):
    try:
        data = json.loads(script.string)
        if isinstance(data, dict) and data.get("@type") == "WeatherForecast":
            json_ld = data
            break
    except Exception:
        continue

current_temp = None
current_cond = None
forecast = []

if json_ld:
    current = json_ld.get("weatherCondition", {})
    current_temp = current.get("temperature")
    current_cond = current.get("description")

    for day in json_ld.get("forecast", [])[:7]:
        forecast.append({
            "day": day.get("dayOfWeek"),
            "min": day.get("lowTemperature"),
            "max": day.get("highTemperature"),
            "condition": day.get("weatherCondition")
        })

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
    "forecast_7d": forecast
}

with open("idokep.json", "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print("Időkép JSON frissítve (JSON-LD)")
