
import requests
from bs4 import BeautifulSoup

URL = "https://www.tvmustra.hu/este?cat=film"

HEADERS = {
    "User-Agent": "Mozilla/5.0"
}

response = requests.get(
    URL,
    headers=HEADERS,
    timeout=30
)
response.raise_for_status()

soup = BeautifulSoup(response.text, "html.parser")
filmek = soup.find_all("h2")

print("====================================")
print("          ESTI FILMEK")
print("====================================")
print("HTTP:", response.status_code)
print("Talalt filmcimek:", len(filmek))

# Megnezzuk az elso harom film HTML-felepiteset.
for szam, film in enumerate(filmek[:3], start=1):

    print(f"\n========== FILM {szam} ==========")
    print("CIM:", film.get_text(" ", strip=True))

    elem = film

    # A film cimet korulvevo HTML-elemek.
    for szint in range(1, 5):

        elem = elem.parent

        if elem is None:
            break

        print(f"\n--- SZULO {szint} ---")
        print("TAG:", elem.name)
        print("CLASS:", elem.get("class"))

        print(
            "SZOVEG:",
            elem.get_text(" ", strip=True)[:300]
        )

        kepek = elem.find_all("img")

        print("KEPEK SZAMA:", len(kepek))

        for kep in kepek[:4]:
            print("  ALT:", kep.get("alt"))
            print("  SRC:", kep.get("src"))
            print("  DATA-SRC:", kep.get("data-src"))
            print("  SRCSET:", kep.get("srcset"))

print("\nFELDOLGOZAS BEFEJEZVE")
