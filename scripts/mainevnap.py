import json
import os
from datetime import datetime
from zoneinfo import ZoneInfo

# -----------------------------
# ALAP ADATOK
# -----------------------------
FORRAS = "mainevnap.hu"
IDŐZÓNA = ZoneInfo("Europe/Budapest")
MA = datetime.now(IDŐZÓNA).date().isoformat()

KIMENET = "mainevnap.json"

# -----------------------------
# NAPI FUTÁS VÉDELEM
# -----------------------------
if os.path.exists(KIMENET):
    with open(KIMENET, "r", encoding="utf-8") as f:
        regi = json.load(f)

    if regi.get("datum") == MA:
        print("Mai névnap már friss.")
        exit(0)

# -----------------------------
# IDE JÖN MAJD A SCRAPELT ADAT
# (most még csak üres)
# -----------------------------
adat = {
    "forras": FORRAS,
    "datum": MA,
    "mai_nevnap": None,
    "eredet": None,
    "jelentese": None
}

# -----------------------------
# JSON MENTÉS
# -----------------------------
with open(KIMENET, "w", encoding="utf-8") as f:
    json.dump(adat, f, ensure_ascii=False, indent=2)

print("Mai névnap JSON létrehozva.")
