
import json
from datetime import datetime

import requests
from bs4 import BeautifulSoup


URL_HOROSZKOP = "https://nlc.hu/horoszkop_napi/"

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

    valasz = requests.get(
        url,
        headers=fejlec,
        timeout=30
    )

    valasz.raise_for_status()

    return BeautifulSoup(
        valasz.text,
        "html.parser"
    )

def horoszkop_adatok(leves):

    horoszkopok = []

    elemek = leves.find_all("div", class_="m-horoscope__item")

    for elem in elemek:

        nev = elem.find("h2", class_="m-horoscope__name")

        datum = elem.find("span", class_="m-horoscope__date")

        szoveg = elem.find("span", class_="m-horoscope__txt")

        if not nev or not datum or not szoveg:
            continue

        horoszkopok.append({
            "nev": nev.get_text(strip=True),
            "datum": datum.get_text(" ", strip=True),
            "szoveg": szoveg.get_text(" ", strip=True)
        })

    return horoszkopok
