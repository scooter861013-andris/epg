import json
from datetime import datetime

import requests
from bs4 import BeautifulSoup


URL_AGROINFORM = "https://www.agroinform.hu/uzemanyagarak"

URL_OMV = "https://holtankoljak.hu/omv_debrecen_828#tartalom"

URL_MOL = "https://holtankoljak.hu/mol_debrecen_151#tartalom"

URL_SHELL = "https://holtankoljak.hu/shell_debrecen_555#tartalom"


def letolt(url):
    fejlec = {
        "User-Agent": (
            "Mozilla/5.0 "
            "(Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 "
            "(KHTML, like Gecko) "
            "Chrome/138.0 Safari/537.36"
        )
    }

    valasz = requests.get(url, headers=fejlec, timeout=30)
    valasz.raise_for_status()

    return BeautifulSoup(valasz.text, "html.parser")


def main():

    print("Agroinform letöltése...")
    agro = letolt(URL_AGROINFORM)

    print("OMV letöltése...")
    omv = letolt(URL_OMV)

    print("MOL letöltése...")
    mol = letolt(URL_MOL)

    print("Shell letöltése...")
    shell = letolt(URL_SHELL)

    adatok = {
        "utolso_frissites": datetime.now().strftime("%Y.%m.%d. %H:%M:%S"),

        "agroinform": {},

        "kutak": []
    }

    with open("uzemanyag.json", "w", encoding="utf-8") as fajl:
        json.dump(
            adatok,
            fajl,
            ensure_ascii=False,
            indent=4
        )

    print("uzemanyag.json elkészült.")


if __name__ == "__main__":
    main()
