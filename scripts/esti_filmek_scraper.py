
import requests
from bs4 import BeautifulSoup

URL = "https://www.tvmustra.hu/este?cat=film"

HEADERS = {
    "User-Agent": "Mozilla/5.0"
}


def main():
    print("====================================")
    print("      ESTI FILMEK - ELSO TESZT")
    print("====================================")

    response = requests.get(
        URL,
        headers=HEADERS,
        timeout=30
    )
    response.raise_for_status()

    print(f"HTTP allapot: {response.status_code}")
    print(f"Letoltott adat: {len(response.content)} byte")

    soup = BeautifulSoup(response.text, "html.parser")

    filmek = soup.find_all("h2")

    print(f"\nTalalt H2 cimek: {len(filmek)}")

    print("\n--- EL SO 15 CIM ---")

    for film in filmek[:15]:
        print("-", film.get_text(" ", strip=True))

    kepek = soup.find_all("img")

    print(f"\nTalalt kepek: {len(kepek)}")

    print("\n--- EL SO 10 KEP ---")

    for kep in kepek[:10]:
        print("ALT:", kep.get("alt", ""))
        print(
            "URL:",
            kep.get("src")
            or kep.get("data-src")
            or "NINCS"
        )
        print("--------------------")

    print("\nTESZT BEFEJEZVE")


if __name__ == "__main__":
    main()
