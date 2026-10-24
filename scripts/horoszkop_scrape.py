
import json
from datetime import datetime
from zoneinfo import ZoneInfo

import requests
from bs4 import BeautifulSoup


URL_HOROSZKOP = "https://nlc.hu/horoszkop_napi/"

CSILLAGJEGYEK = {
    "kos": "Kos",
    "bika": "Bika",
    "ikrek": "Ikrek",
    "rak": "Rák",
    "oroszlan": "Oroszlán",
    "szuz": "Szűz",
    "merleg": "Mérleg",
    "skorpio": "Skorpió",
    "nyilas": "Nyilas",
    "bak": "Bak",
    "vizonto": "Vízöntő",
    "halak": "Halak"
}


def letolt(url):
    fejlec = {
        "User-Agent": (
            "Mozilla/5.0 "
            "(Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 "
            "(KHTML, like Gecko) "
            "Chrome/138.0 Safari/537.36"
        ),
        "Accept-Language": "hu-HU,hu;q=0.9"
    }

    valasz = requests.get(
        url,
        headers=fejlec,
        timeout=30
    )

    print("HTTP válasz:", valasz.status_code)
    valasz.raise_for_status()

    return BeautifulSoup(
        valasz.text,
        "html.parser"
    )


def horoszkop_adatok(leves):
    horoszkopok = []

    for azonosito, nev in CSILLAGJEGYEK.items():

        elem = leves.find(
            "article",
            id=azonosito
        )

        if not elem:
            print("HIÁNYZIK:", nev)
            continue

        nev_elem = elem.find(
            "p",
            class_=lambda c: c and
            "horop:font-heading" in c
        )

        datum_elem = elem.find(
            "p",
            class_=lambda c: c and
            "horop:whitespace-nowrap" in c
        )

        szoveg_elem = elem.find(
            "p",
            class_=lambda c: c and
            "horop:text-lg" in c
        )

        if not all([
            nev_elem,
            datum_elem,
            szoveg_elem
        ]):
            print("HIÁNYOS ADAT:", nev)
            continue

        talalt_nev = nev_elem.get_text(strip=True)
        datum = datum_elem.get_text(" ", strip=True)
        szoveg = szoveg_elem.get_text(" ", strip=True)

        if talalt_nev != nev or not datum or not szoveg:
            print("HIBÁS ADAT:", nev)
            continue

        horoszkopok.append({
            "nev": nev,
            "datum": datum,
            "szoveg": szoveg
        })

        print("OK:", nev)

    return horoszkopok


def main():
    print("Horoszkóp letöltése...")

    oldal = letolt(URL_HOROSZKOP)

    horoszkopok = horoszkop_adatok(oldal)

    print(
        "Talált horoszkópok:",
        len(horoszkopok)
    )

    if len(horoszkopok) != 12:
        raise RuntimeError(
            "HIBA: Nem található mind a "
            "12 horoszkóp! JSON nem készül."
        )

    adatok = {
        "utolso_frissites": datetime.now(
            ZoneInfo("Europe/Budapest")
        ).strftime("%Y.%m.%d. %H:%M:%S"),
        "horoszkopok": horoszkopok
    }

    with open(
        "horoszkop.json",
        "w",
        encoding="utf-8"
    ) as fajl:
        json.dump(
            adatok,
            fajl,
            ensure_ascii=False,
            indent=4
        )

    print("horoszkop.json elkészült.")


if __name__ == "__main__":
    main()
    
