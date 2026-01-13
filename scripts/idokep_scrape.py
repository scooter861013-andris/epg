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
        current_temp = int(
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
# NAPKELTE / NAPNYUGTA
# -------------------------------------------------
sunrise = None
sunset = None

# Napkelte
sunrise_el = soup.find("img", alt="Napkelte")
if sunrise_el:
    text = sunrise_el.parent.get_text(strip=True)
    m = re.search(r"Napkelte\s*(\d{1,2}:\d{2})", text)
    if m:
        sunrise = m.group(1)

# Napnyugta
sunset_el = soup.find("img", alt="Napnyugta")
if sunset_el:
    text = sunset_el.parent.get_text(strip=True)
    m = re.search(r"Napnyugta\s*(\d{1,2}:\d{2})", text)
    if m:
        sunset = m.group(1)

# -------------------------------------------------
# 7 NAPOS ELŐREJELZÉS  ✅ HELYES IDŐKÉP DOM
# -------------------------------------------------
def parse_temp(card, cls):
    el = card.select_one(f".{cls}")
    if not el:
        return None
    txt = el.get_text(strip=True)
    try:
        return int(txt)
    except ValueError:
        return None
forecast_7d = []
cards = soup.select(".ik.dailyForecastCol")[:7]
for card in cards:
    day = None
    tmin = None
    tmax = None
    condition = None
    icon = None
    alert = None
    close = None

    # --- FIGYELMEZTETÉS ---
    alert_icon = card.select_one(".forecast-alert-icon")
    if alert_icon:
        a_el = card.select_one(".dfIconAlert a")
        if a_el and a_el.has_attr("data-bs-content"):
            html = a_el["data-bs-content"]

            lines = re.findall(
                r"fc-line[^>]*>.*?</div>",
                html,
                flags=re.DOTALL
            )

            for line in lines:
                if "figyikonok2" in line:
                    txt = re.sub(r".*?>", "", line)   # minden HTML elejét levágja
                    txt = re.sub(r"<[^>]+>", "", txt) # maradék tagek le
                    alert = txt.strip()
                    break

    # nap
    a_el = card.select_one(".dfIconAlert a")
    if a_el and a_el.has_attr("title"):
        title = a_el["title"]

    # pl: "Szombat<br>2026. január 3."
        parts = title.split("<br>")
        day = title.split(" ")[0] if parts else None


    tmin = parse_temp(card, "min")
    tmax = parse_temp(card, "max")

    # --- KEDD / összevont min-max (min-max-close) ---
    if tmin is None and tmax is None:
        close = card.select_one(".min-max-line")
      #  close = card.select_one(".min-max-close")
        if close:
            vals = [v.get_text(strip=True) for v in close.select("a")]
            vals = [v.replace("−", "-") for v in vals]

            try:
                nums = [int(v) for v in vals if v]
                if len(nums) >= 2:
                    tmax = nums[0]
                    tmin = nums[1]
            except ValueError:
                pass
                
        # --- HELYES FALLBACK: NAPI MIN / MAX AZ <a> SZÖVEGÉBŐL ---
    if tmin is None and tmax is None and close:
        vals = [a.get_text(strip=True).replace("−", "-") for a in close.select("a")]
        nums = [int(v) for v in vals if re.fullmatch(r"-?\d+", v)]
        if len(nums) == 2:
            tmax = max(nums)
            tmin = min(nums)

    
    # --- UTOLSÓ, VÉGLEGES MIN/MAX MENTÉS ---
    if tmin is None and tmax is None:
        vals = []
        for a in card.select("a"):
            txt = a.get_text(strip=True).replace("−", "-")
            if re.fullmatch(r"-?\d+", txt):
                vals.append(int(txt))

        if len(vals) >= 2:
            tmin = min(vals)
            tmax = max(vals)

    
    #    if len(temps) >= 2:
    #        tmax = temps[0]
       #     tmin = temps[1]

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
        "icon": icon,
        "alert": alert
    })

# -------------------------------------------------
# JSON KIMENET
# -------------------------------------------------

old_data = None
if os.path.exists("idokep.json"):
    with open("idokep.json", "r", encoding="utf-8") as f:
        old_data = json.load(f)
now = datetime.now(ZoneInfo("Europe/Budapest")).strftime("%Y.%m.%d. %H:%M")
now_dt = datetime.now(ZoneInfo("Europe/Budapest"))
is_night = None
if sunrise and sunset:
    sr = datetime.strptime(sunrise, "%H:%M").time()
    ss = datetime.strptime(sunset, "%H:%M").time()
    now_t = now_dt.time()

    # nappal: napkelte <= most < napnyugta
    is_night = not (sr <= now_t < ss)

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
    "forecast_7d": forecast_7d,
    "sun": {
    "sunrise": sunrise,
    "sunset": sunset,
    "is_night": is_night
},
}

with open("idokep.json", "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print("Időkép JSON frissítve (aktuális + 7 napos előrejelzés)")
