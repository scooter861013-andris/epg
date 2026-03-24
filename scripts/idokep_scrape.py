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

temp_el = soup.select_one(".ik.current-temperature")

if temp_el:
    text = temp_el.get_text(strip=True)
    m = re.search(r"-?\d+", text)
    if m:
        current_temp = int(m.group())

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

sunrise_div = soup.select_one(".icon.sunrise")
if sunrise_div:
    text = sunrise_div.get_text(strip=True)
    m = re.search(r"(\d{1,2}:\d{2})", text)
    if m:
        sunrise = m.group(1)

sunset_div = soup.select_one(".icon.sunset")
if sunset_div:
    text = sunset_div.get_text(strip=True)
    m = re.search(r"(\d{1,2}:\d{2})", text)
    if m:
        sunset = m.group(1)

# -------------------------------------------------
# FRONTHATÁS (STABIL)
# -------------------------------------------------
fronthatas = None

front_el = soup.select_one(".scTextDescription")
if front_el:
    fronthatas = front_el.get_text(strip=True)

# -------------------------------------------------
# FŐCÍM
# -------------------------------------------------
focim = None

focim_el = soup.select_one(".shortWeatherTitle")

if focim_el:
    focim = focim_el.get_text(strip=True)


# -------------------------------------------------
# 7 NAPOS ELŐREJELZÉS  ✅ HELYES IDŐKÉP DOM
# -------------------------------------------------
def parse_temp(card, cls):
    el = card.select_one(f".{cls}")
    if not el:
        return None
    txt = el.get_text(strip=True).replace("−", "-")
    try:
        return round(float(txt))
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
                    
# --- NAPNÉV PONTOS (DÁTUM ALAPJÁN) ---
    daynum_el = card.select_one(".dfDayNum")

    if daynum_el:
        try:
            day_number = int(daynum_el.get_text(strip=True))

            now_dt = datetime.now(ZoneInfo("Europe/Budapest"))
            year = now_dt.year
            month = now_dt.month

            # ha a következő hónapba csúszik
            if day_number < now_dt.day:
                if month == 12:
                    month = 1
                    year += 1
                else:
                    month += 1

            date_obj = datetime(year, month, day_number)

            weekday_en = date_obj.strftime("%A")

            DAY_TRANSLATE = {
                "Monday": "Hétfő",
                "Tuesday": "Kedd",
                "Wednesday": "Szerda",
                "Thursday": "Csütörtök",
                "Friday": "Péntek",
                "Saturday": "Szombat",
                "Sunday": "Vasárnap"
            }

            day = DAY_TRANSLATE.get(weekday_en, weekday_en)

        except:
            pass
            
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
        "max": tmax,
        "min": tmin,
        "condition": condition,
        "icon": icon,
        "alert": alert
    })


# -------------------------------------------------
# ÓRÁS ELŐREJELZÉS (külön lekérésből)
# -------------------------------------------------
# -------------------------------------------------
# ÓRÁS ELŐREJELZÉS (VALÓDI FORRÁS)
# -------------------------------------------------
hourly = []

try:
    api_url = f"https://www.idokep.hu/api/forecast/{LOCATION}"
    r = requests.get(api_url, timeout=10)
    r.raise_for_status()
    data_api = r.json()

    print("API KEYS:", data_api.keys())  # debug

    if "hourly" in data_api:
        for h in data_api["hourly"][:12]:
            hourly.append({
                "ido": h.get("time"),
                "varhato_homerseklet": h.get("temp"),
                "korulmeny": h.get("weather")
            })

except Exception as e:
    print("API hiba:", e)


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
    "hourly": hourly,
    "fronthatas": fronthatas,
    "focim": focim,
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
