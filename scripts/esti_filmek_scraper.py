import json
import re
from datetime import datetime
from zoneinfo import ZoneInfo
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup


URL = "https://www.tvmustra.hu/este?cat=film"
BASE_URL = "https://www.tvmustra.hu"

HEADERS = {
    "User-Agent": "Mozilla/5.0"
}

# Csak azok a csatornák, amik nálad érdekesek lehetnek
ENGEDLYEZETT_CSATORNAK = {
    "Film+",
    "PRIME",
    "Magyar Mozi TV",
    "Mozi+",
    "Film Café",
    "AXN",
    "AMC",
    "Cool TV",
    "Moziverzum",
    "Moziklub",
    "JockyTV",
    "FILMBOX+ comedy",
    "FILMBOX+ love&crime",
    "FILMBOX+ one",
    "FILMBOX+ emotion HD",
    "RTL GOLD",
    "AXN Crime",
    "Viasat 2",
    "Izaura TV",
    "Viasat Epic Drama",
    "Film Mánia",
    "Film4",
    "MAX4",
    "Telekom FilmKlub",
    "TV2",
    "RTL",
    "Viasat 3",
    "RTL KETTŐ",
    "Super TV2",
    "Story4",
    "TV4",
    "Viasat 6",
    "RTL HÁROM"
}


def szoveg(el):
    if not el:
        return ""
    return el.get_text(" ", strip=True)


def tisztit_url(url):
    if not url:
        return ""
    return urljoin(BASE_URL, url.strip())


def csatorna_nev_kepbol(img_alt):
    if not img_alt:
        return ""
    return re.sub(r"\s+logó$", "", img_alt.strip(), flags=re.IGNORECASE)


def filmek_kinyerese(soup):
    eredmeny = []
    kartyak = soup.select("div.este-card")

    for kartya in kartyak:
        cim_el = kartya.find("h2")
        cim = szoveg(cim_el)

        if not cim:
            continue

        teljes_szoveg = kartya.get_text(" ", strip=True)

        # időpont
        ido = ""
        m_ido = re.search(r"\b(\d{1,2}:\d{2})\b", teljes_szoveg)
        if m_ido:
            ido = m_ido.group(1)

        # műfaj zárójelből
        mufaj = ""
        m_mufaj = re.search(r"\(([^)]+)\)", teljes_szoveg)
        if m_mufaj:
            mufaj = m_mufaj.group(1).strip()

        # képek
        borito_kep = ""
        csatorna_logo = ""
        csatorna = ""

        for img in kartya.find_all("img"):
            alt = (img.get("alt") or "").strip()
            src = img.get("src") or img.get("data-src") or ""

            if "/logok/" in src or alt.lower().endswith("logó"):
                csatorna_logo = tisztit_url(src)
                if not csatorna:
                    csatorna = csatorna_nev_kepbol(alt)
            else:
                if not borito_kep:
                    borito_kep = tisztit_url(src)

        # leírás
        leiras = ""
        bekezdesek = [szoveg(p) for p in kartya.find_all("p")]
        bekezdesek = [b for b in bekezdesek if b]

        if bekezdesek:
            leiras = max(bekezdesek, key=len)

        # ha valamiért nincs csatorna, próbáljuk szövegből
        if not csatorna:
            for nev in ENGEDLYEZETT_CSATORNAK:
                if nev in teljes_szoveg:
                    csatorna = nev
                    break

        # ha nem a saját / érdekes csatornák között van, kihagyjuk
        if csatorna and csatorna not in ENGEDLYEZETT_CSATORNAK:
            continue

        eredmeny.append({
            "idopont": ido,
            "cim": cim,
            "csatorna": csatorna,
            "mufaj": mufaj,
            "leiras": leiras,
            "kep": borito_kep,
            "csatorna_logo": csatorna_logo,
            "van_borito": bool(borito_kep)
        })

    return eredmeny


def main():
    response = requests.get(URL, headers=HEADERS, timeout=30)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")
    filmek = filmek_kinyerese(soup)

    adatok = {
        "utolso_frissites": datetime.now(ZoneInfo("Europe/Budapest")).strftime("%Y.%m.%d. %H:%M:%S"),
        "forras": URL,
        "darab": len(filmek),
        "filmek": filmek
    }

    with open("esti_filmek.json", "w", encoding="utf-8") as fajl:
        json.dump(adatok, fajl, ensure_ascii=False, indent=4)

    print("esti_filmek.json elkészült.")
    print("Talált filmek száma:", len(filmek))


if __name__ == "__main__":
    main()
