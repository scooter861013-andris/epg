import json
import re
from datetime import datetime
from zoneinfo import ZoneInfo
import requests
from bs4 import BeautifulSoup

# -----------------------------
# ALAP ADATOK
# -----------------------------
FORRAS = "mainevnap.hu"
IDOZONA = ZoneInfo("Europe/Budapest")
MA = datetime.now(IDOZONA).date().isoformat()

KIMENET = "mainevnap.json"

# -----------------------------
# OLDAL LETÖLTÉS
# -----------------------------
URL = "https://mainevnap.hu/"

resp = requests.get(
    URL,
    timeout=15,
    headers={
        "User-Agent": "Mozilla/5.0"
    }
)

resp.raise_for_status()

soup = BeautifulSoup(
    resp.text,
    "html.parser"
)

print("Oldal letöltve.")

# -----------------------------
# ADAT STRUKTÚRA
# -----------------------------
frissites_ido = datetime.now(IDOZONA).strftime("%Y.%m.%d - %H:%M")

adat = {
    "forras": FORRAS,
    "datum": MA,
    "mai_nevnap": None,
    "eredet": None,
    "jelentese": None,
    "frissitve": frissites_ido
}

# -----------------------------
# MAI NÉVNAP KIOLVASÁSA
# -----------------------------
nev_el = soup.select_one("span.piroskiem")

if nev_el:
    adat["mai_nevnap"] = nev_el.get_text(strip=True)

# -----------------------------
# EREDET + JELENTÉS (KÜLÖN MEZŐK)
# -----------------------------
teljes_szoveg = soup.get_text(" ", strip=True)
nev = adat["mai_nevnap"]

if nev:
    m = re.search(
        rf"{nev} eredete:\s*(.+?);\s*jelentése:\s*(.+?\.)",
        teljes_szoveg
    )

    if m:
        # EREDET
        eredet_szoveg = m.group(1).strip()
        eredet_szoveg = re.sub(r"\s*eredetű\s*$", "", eredet_szoveg)
        eredet_szoveg = eredet_szoveg[:1].upper() + eredet_szoveg[1:]

        adat["eredet"] = eredet_szoveg

        # JELENTÉS (1 mondat)
        adat["jelentese"] = m.group(2).strip()

# -----------------------------
# JSON MENTÉS
# -----------------------------
with open(KIMENET, "w", encoding="utf-8") as f:
    json.dump(adat, f, ensure_ascii=False, indent=2)

print("Mai névnap JSON létrehozva.")
