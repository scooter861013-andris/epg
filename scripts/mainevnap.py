import json
import os
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
adat = {
    "forras": FORRAS,
    "datum": MA,
    "mai_nevnap": None,
    "eredet": None,
    "jelentese": None
}

# -----------------------------
# MAI NÉVNAP KIOLVASÁSA
# -----------------------------
nev_el = soup.select_one("span.piroskiem")

if nev_el:
    adat["mai_nevnap"] = nev_el.get_text(strip=True)

# -----------------------------
# EREDET + JELENTÉS (1-1 mondat)
# -----------------------------
teljes_szoveg = soup.get_text(" ", strip=True)

nev = adat["mai_nevnap"]

if nev:
    # EREDET (két sorba törve)
    m1 = re.search(
        rf"{nev} eredete:\s*(.+?\.)",
        teljes_szoveg
    )
    if m1:
        adat["eredet"] = (
            m1.group(1)
            .replace("; jelentése:", ";\n\njelentése:")
            .strip()
        )

    # JELENTÉS (külön, hosszú szöveg első mondata)
    m2 = re.search(
        rf"{nev} jelentése:\s*(.+?\.)",
        teljes_szoveg
    )
    if m2:
        adat["jelentese"] = m2.group(1).strip()

# -----------------------------
# JSON MENTÉS
# -----------------------------
with open(KIMENET, "w", encoding="utf-8") as f:
    json.dump(adat, f, ensure_ascii=False, indent=2)

print("Mai névnap JSON létrehozva.")
