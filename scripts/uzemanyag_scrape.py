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


def agroinform_adatok(leves):

    adatok = {}

    dobozok = leves.find_all("div", class_="exchange_rate_box")

    for doboz in dobozok:

        szoveg = doboz.get_text(" ", strip=True)

        if "Gázolaj árak" in szoveg:

            ar = doboz.find("div", class_="price").get_text(strip=True)
            ar = ar.replace("Ft", "").strip()

            if "rate_up" in doboz.get("class", []):
                irany = "novekedett"
            else:
                irany = "csokkent"

            adatok["gazolaj"] = {
                "ar": ar,
                "irany": irany
            }

        elif "Benzin árak" in szoveg:

            ar = doboz.find("div", class_="price").get_text(strip=True)
            ar = ar.replace("Ft", "").strip()

            if "rate_up" in doboz.get("class", []):
                irany = "novekedett"
            else:
                irany = "csokkent"

            adatok["benzin95"] = {
                "ar": ar,
                "irany": irany
            }

        elif "EUR" in szoveg:

            ar = doboz.find("span", class_="rate").get_text(strip=True)
            ar = ar.replace("Ft", "").strip()

            if "rate_up" in doboz.get("class", []):
                irany = "novekedett"
            else:
                irany = "csokkent"

            adatok["eur"] = {
                "ar": ar,
                "irany": irany
            }

        elif "USD" in szoveg:

            ar = doboz.find("span", class_="rate").get_text(strip=True)
            ar = ar.replace("Ft", "").strip()

            if "rate_up" in doboz.get("class", []):
                irany = "novekedett"
            else:
                irany = "csokkent"

            adatok["usd"] = {
                "ar": ar,
                "irany": irany
            }

    return adatok

def kut_adatok(leves):

    kut = {
        "marka": "",
        "cim": "",
        "uzemanyagok": []
    }

    cim = leves.find("span", class_="subpage")

    if cim:
        kut["cim"] = cim.get_text(strip=True)

    logo = leves.find("img", src=lambda s: s and "partner_logo" in s)

    if logo:

        marka = logo.get("title", "").strip().upper()

        if marka == "OMV":
            kut["marka"] = "OMV"

        elif marka == "MOL":
            kut["marka"] = "MOL"

        elif marka == "SHELL":
            kut["marka"] = "Shell"

        else:
            kut["marka"] = marka



    
    sorok = leves.find_all("div", class_="d-flex mb-3")

    for sor in sorok:

        ikon = sor.find("img")

        if not ikon:
            continue

        kep = ikon.get("src", "")

        if "ua_pin" not in kep:
            continue

        datum = sor.find("span", class_="badge")

        ar = sor.find("span", class_="ar")

        if not datum or not ar:
            continue

        datum = datum.get_text(strip=True)

        ar = ar.get_text(" ", strip=True)

        if "premium_gazolaj" in kep:
            tipus = "Dízel (Premium B7)"

        elif "premium-benzin-e10" in kep:
            tipus = "95 (Premium E10)"

        elif "100-benzin-e5" in kep:
            tipus = "100 (E5)"

        elif "95-benzin-e10" in kep:
            tipus = "95 (E10)"

        elif "gazolaj" in kep:
            tipus = "Dízel (B7)"

        else:
            continue

        kut["uzemanyagok"].append({
            "datum": datum,
            "tipus": tipus,
            "ar": ar
        })
    
    return kut
    

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

        "agroinform": agroinform_adatok(agro),

        "kutak": []
    }

    
    adatok["kutak"].append(kut_adatok(omv))
    adatok["kutak"].append(kut_adatok(mol))
    adatok["kutak"].append(kut_adatok(shell))
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
