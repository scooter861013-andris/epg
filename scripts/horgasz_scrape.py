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
URL = "[idokep.hu](https://www.idokep.hu/horgasz)"

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
# NAPKELTE / NAPNYUGTA / HOLDKELTE / HOLDNYUGTA
# -------------------------------------------------
nap_hold = {}
for item in soup.select(".ik.sunrise-header-item"):
    strong = item.find("strong")
    if not strong:
        continue
    ertek = strong.get_text(strip=True)
    cimke = item.get_text(strip=True).replace(ertek, "").strip()
    nap_hold[cimke] = ertek

napkelte = nap_hold.get("Napkelte")
napnyugta = nap_hold.get("Napnyugta")
holdkelte = nap_hold.get("Holdkelte")
holdnyugta = nap_hold.get("Holdnyugta")

# -------------------------------------------------
# SEGÉDFÜGGVÉNYEK
# -------------------------------------------------
def kod_kinyerese_src_bol(src):
    """/assets/forecastIcons/090.svg -> '090' | /images/holdfazis/7.svg -> '7'"""
    if not src:
        return None
    m = re.search(r"/([^/]+)\.svg$", src)
    return m.group(1) if m else None


def egesz_szam(szoveg):
    if szoveg is None:
        return None
    szoveg = szoveg.strip().replace("−", "-")
    try:
        return int(szoveg)
    except ValueError:
        return None


# -------------------------------------------------
# KAPÁSINDEX OSZLOPOK (Most, Szombat reggel, ... stb.)
# -------------------------------------------------
elorejelzes = []

for kartya in soup.select(".ik.fishing-column"):
    fejlec_el = kartya.select_one(".fishing-column-header")
    idoszak = fejlec_el.get_text(strip=True) if fejlec_el else None

    egkep_img = kartya.select_one(".fishing-column-forecast-icon img")
    egkep_ikon = kod_kinyerese_src_bol(egkep_img["src"]) if egkep_img and egkep_img.has_attr("src") else None

    hold_img = kartya.select_one(".fishing-column-moonphase img")
    holdfazis_kod = kod_kinyerese_src_bol(hold_img["src"]) if hold_img and hold_img.has_attr("src") else None
    holdfazis = egesz_szam(holdfazis_kod) if holdfazis_kod is not None else None

    kapasindex_el = kartya.select_one(".fishing-column-temperature .tempValue")
    kapasindex = egesz_szam(kapasindex_el.get_text(strip=True)) if kapasindex_el else None

    hal_span = kartya.select_one(".fishing-column-kapasindex span")
    halikonok_szama = hal_span.get_text(strip=True).count("🐟") if hal_span else None

    ertekeles_el = kartya.select_one(".fishing-column-ertekeles .pill")
    minosites = ertekeles_el.get_text(strip=True) if ertekeles_el else None

    elorejelzes.append({
        "időszak": idoszak,
        "égkép_ikon": egkep_ikon,
        "holdfázis": holdfazis,
        "kapásindex": kapasindex,
        "halikonok_száma": halikonok_szama,
        "minősítés": minosites
    })

# -------------------------------------------------
# VALIDÁCIÓ - NE ÍRJUNK FELÜL JÓ ADATOT ROSSZAL
# -------------------------------------------------
if not napkelte or not napnyugta:
    raise SystemExit("Hiba: nap/hold adatok nem olvashatók, az oldal szerkezete valószínűleg megváltozott. Megszakítva.")

if not elorejelzes or not any(e["kapásindex"] is not None for e in elorejelzes):
    raise SystemExit("Hiba: kapásindex adatok nem olvashatók, az oldal szerkezete valószínűleg megváltozott. Megszakítva.")

# -------------------------------------------------
# JSON KIMENET
# -------------------------------------------------
regi_adat = None
if os.path.exists("horgasz.json"):
    with open("horgasz.json", "r", encoding="utf-8") as f:
        regi_adat = json.load(f)

most = datetime.now(ZoneInfo("Europe/Budapest")).strftime("%Y.%m.%d. %H:%M")

adat = {
    "forrás": "idokep.hu",
    "hivatkozás": URL,
    "utoljára_változott_kapásindex": (
        regi_adat.get("utoljára_változott_kapásindex")
        if regi_adat and regi_adat.get("előrejelzés") == elorejelzes
        else most
    ),
    "utolsó_futás": most,
    "nap_és_hold": {
        "napkelte": napkelte,
        "napnyugta": napnyugta,
        "holdkelte": holdkelte,
        "holdnyugta": holdnyugta
    },
    "előrejelzés": elorejelzes
}

with open("horgasz.json", "w", encoding="utf-8") as f:
    json.dump(adat, f, ensure_ascii=False, indent=2)

print("Horgász JSON frissítve (kapásindex előrejelzés)")
