
import csv
import json
import hashlib
import sys
from datetime import datetime
from pathlib import Path
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

from bs4 import BeautifulSoup


# ==========================================
# TVMUSTRA ESTI FILMEK FIGYELŐ
# ==========================================

URL = "https://www.tvmustra.hu/este?cat=film"

IDŐZÓNA = ZoneInfo("Europe/Budapest")

# GitHub repository főmappája
GYOKER = Path(__file__).resolve().parent.parent

ALLAPOT_FAJL = GYOKER / "tvmustra_allapot.json"
NAPLO_FAJL = GYOKER / "tvmustra_valtozasok.csv"

HEADERS = {
    "User-Agent": "Mozilla/5.0"
}

# ==========================================
# SEGÉDFÜGGVÉNYEK
# ==========================================

def most():
    return datetime.now(IDŐZÓNA).isoformat(
        timespec="seconds"
    )


def oldal_letoltese():
    keres = Request(URL, headers=HEADERS)

    with urlopen(keres, timeout=30) as valasz:
        html = valasz.read()

    return BeautifulSoup(html, "html.parser")


# ==========================================
# ESTI FILMEK KINYERÉSE
# ==========================================

def filmek_kinyerese(soup):

    eredmeny = []

    kartyak = soup.select("div.este-card")

    if not kartyak:
        raise RuntimeError(
            "Nem találhatók esti filmkártyák!"
        )

    for kartya in kartyak:

        cim_elem = kartya.find("h2")
        ido_elem = kartya.select_one(
            ".este-time-badge"
        )

        logo_elem = kartya.select_one(
            "img.este-logo-mini"
        )

        csatorna_elem = kartya.select_one(
            ".text-muted.fw-semibold"
        )

        cim = (
            cim_elem.get_text(" ", strip=True)
            if cim_elem else ""
        )

        ido = (
            ido_elem.get_text(" ", strip=True)
            if ido_elem else ""
        )

        csatorna = ""

        if logo_elem:
            csatorna = logo_elem.get(
                "alt", ""
            ).strip()

            if csatorna.lower().endswith(" logó"):
                csatorna = csatorna[:-5].strip()

        if not csatorna and csatorna_elem:
            csatorna = csatorna_elem.get_text(
                " ", strip=True
            )

        if not cim or not ido or not csatorna:
            raise RuntimeError(
                "Hiányos műsorkártya! "
                "A megfigyelés megszakadt."
            )

        eredmeny.append({
            "cim": cim,
            "csatorna": csatorna,
            "idopont": ido
        })

    # A weboldal megjelenítési sorrendje
    # nem számít változásnak.
    eredmeny.sort(
        key=lambda x: (
            x["csatorna"],
            x["idopont"],
            x["cim"]
        )
    )

    return eredmeny


# ==========================================
# ELLENŐRZŐ ÖSSZEG
# ==========================================

def lenyomat(filmek):

    tartalom = json.dumps(
        filmek,
        ensure_ascii=False,
        sort_keys=True
    )

    return hashlib.sha256(
        tartalom.encode("utf-8")
    ).hexdigest()


# ==========================================
# KORÁBBI ÁLLAPOT
# ==========================================

def elozo_allapot():

    if not ALLAPOT_FAJL.exists():
        return None

    with open(
        ALLAPOT_FAJL,
        "r",
        encoding="utf-8"
    ) as fajl:
        return json.load(fajl)


def allapot_mentese(filmek, ellenorzes):

    adatok = {
        "ellenorzes": ellenorzes,
        "darab": len(filmek),
        "lenyomat": lenyomat(filmek),
        "filmek": filmek
    }

    ideiglenes = ALLAPOT_FAJL.with_suffix(
        ".json.tmp"
    )

    with open(
        ideiglenes,
        "w",
        encoding="utf-8"
    ) as fajl:
        json.dump(
            adatok,
            fajl,
            ensure_ascii=False,
            indent=4
        )

    ideiglenes.replace(ALLAPOT_FAJL)


# ==========================================
# VÁLTOZÁSOK NAPLÓZÁSA
# ==========================================

def naplozas(
    ellenorzes,
    regi_db,
    uj_db,
    hozzaadott,
    eltunt
):

    uj_fajl = not NAPLO_FAJL.exists()

    with open(
        NAPLO_FAJL,
        "a",
        encoding="utf-8-sig",
        newline=""
    ) as fajl:

        iro = csv.writer(fajl, delimiter=";")

        if uj_fajl:
            iro.writerow([
                "Észlelés időpontja",
                "Korábbi műsorok",
                "Új műsorok",
                "Hozzáadott",
                "Eltűnt"
            ])

        iro.writerow([
            ellenorzes,
            regi_db,
            uj_db,
            " | ".join(hozzaadott),
            " | ".join(eltunt)
        ])


# ==========================================
# FŐPROGRAM
# ==========================================

def main():

    ellenorzes = most()

    print("=" * 55)
    print("TVmustra esti filmek figyelő")
    print("Ellenőrzés:", ellenorzes)

    soup = oldal_letoltese()

    uj_filmek = filmek_kinyerese(soup)
    uj_lenyomat = lenyomat(uj_filmek)

    regi = elozo_allapot()

    # ELSŐ FUTÁS
    if regi is None:

        allapot_mentese(
            uj_filmek,
            ellenorzes
        )

        print(
            "Első mérés:",
            len(uj_filmek),
            "műsor."
        )

        print("Kiindulási állapot elmentve.")
        return

    # NINCS VÁLTOZÁS
    if regi.get("lenyomat") == uj_lenyomat:

        print(
            "Nincs változás.",
            len(uj_filmek),
            "műsor."
        )

        return

    # VÁLTOZÁS VAN!
    regi_filmek = regi.get("filmek", [])

    def azonosito(film):
        return (
            film["csatorna"],
            film["idopont"],
            film["cim"]
        )

    regi_halmaz = {
        azonosito(film)
        for film in regi_filmek
    }

    uj_halmaz = {
        azonosito(film)
        for film in uj_filmek
    }

    hozzaadott = sorted(
        uj_halmaz - regi_halmaz
    )

    eltunt = sorted(
        regi_halmaz - uj_halmaz
    )

    def formatum(adat):
        csatorna, ido, cim = adat
        return f"{csatorna} / {ido} / {cim}"

    hozzaadott_szoveg = [
        formatum(adat)
        for adat in hozzaadott
    ]

    eltunt_szoveg = [
        formatum(adat)
        for adat in eltunt
    ]

    print("!!! VÁLTOZÁS ÉSZLELVE !!!")
    print(
        "Korábbi műsorok:",
        len(regi_filmek)
    )
    print(
        "Új műsorok:",
        len(uj_filmek)
    )

    for film in hozzaadott_szoveg:
        print("+", film)

    for film in eltunt_szoveg:
        print("-", film)

    # A változás naplózása
    naplozas(
        ellenorzes,
        len(regi_filmek),
        len(uj_filmek),
        hozzaadott_szoveg,
        eltunt_szoveg
    )

    # Az új állapot megőrzése
    allapot_mentese(
        uj_filmek,
        ellenorzes
    )

    print("Változás elmentve!")


if __name__ == "__main__":

    try:
        main()

    except Exception as hiba:
        print("FIGYELŐ HIBA:", repr(hiba))
        sys.exit(1)
