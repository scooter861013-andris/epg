"""Hajdu-Bihar hirdetesi lista: manualis GitHub Actions JSON export."""
import argparse
import html
import json
import re
from datetime import datetime
from pathlib import Path
from urllib.parse import urljoin
from zoneinfo import ZoneInfo

import requests
from bs4 import BeautifulSoup

URL = 'https://rosszlanyok.hu/rosszlanyok.php?pid=szexpartner-lista&htext=73'
OUT = Path('rossz.json')
HEADERS = {'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36', 'Accept-Language': 'hu-HU,hu;q=0.9'}
COUNTY = 'Hajdú-Bihar'
CITIES = ['Berettyóújfalu', 'Debrecen', 'Hajdúböszörmény', 'Hajdúnánás', 'Hajdúszoboszló', 'Nyíracsád', 'Püspökladány', 'Téglás']


def clean(value):
    return ' '.join(str(value or '').split())


def tooltip_lines(link):
    raw = link.get('onmouseover', '') if link else ''
    match = re.search(r"myToolTip\(\s*'((?:\\.|[^'\\])*)'", raw, re.S)
    if not match:
        return []
    snippet = html.unescape(match.group(1).replace("\\'", "'").replace('\\"', '"'))
    soup = BeautifulSoup(snippet, 'html.parser')
    # A HTML br tagjeit sorhatarra alakitjuk, hogy a helyszin ne keveredjen mas mezokkel.
    for br in soup.find_all('br'):
        br.replace_with('\n')
    return [clean(line) for line in soup.get_text('\n').splitlines() if clean(line) and clean(line) != ',']


def parse_card(card, page_url):
    identifier = clean(card.get('data-memberthumb'))
    name_tag = card.select_one('.nevToShowOnList .nev') or card.select_one('.nev')
    link = card.select_one('a.onExternalAdvThumbLink')
    if not identifier or not name_tag or not link:
        return None
    name_full = clean(name_tag.get_text(' ', strip=True))
    age_match = re.fullmatch(r'(.*?)\s*\((\d+)\)', name_full)
    name = age_match.group(1) if age_match else name_full
    age = int(age_match.group(2)) if age_match else None
    img = card.select_one('img.listTagImage')
    image_path = (img.get('data-src') or img.get('src') or '') if img else ''
    image = urljoin(page_url, image_path) if image_path and 'spacer.gif' not in image_path else None
    lines = tooltip_lines(link)
    # A helyszin a bemutatott hirdeteseknel a nev/kategoria utan, az eletkoros sor elott van.
    location = None
    for index, line in enumerate(lines):
        if re.search(r'\b\d{1,2}\+?\s*éves\b', line, re.I):
            if index > 0:
                candidate = lines[index - 1].strip(' ,')
                if candidate and not any(k in candidate.casefold() for k in ('lány', 'szexpartner', 'masszázs', 'dominák')):
                    location = candidate
            break
    if not location and img:
        alt = clean(img.get('alt', ''))
        match = re.search(re.escape(name) + r'\s+(.+?)\s+(?:szexpartner|masszázs|dominák)\s+lányok', alt, re.I)
        if match:
            location = clean(match.group(1))
    # Sem a telepules, sem a testsuly nem tippelheto meg hianyzo adat eseten.
    city = location.split(',')[0].strip() if location else None
    weight_match = re.search(r'\b\d{1,2}\+?\s*éves\b[^\n]*?\b\d{2,3}\s*cm\s*,\s*(\d{2,3}\+?)\s*kg\b', '\n'.join(lines), re.I)
    weight = weight_match.group(1) + ' kg' if weight_match else None
    today = next((clean(x.split(':', 1)[1]) for x in lines if x.lower().startswith('ma:')), None)
    alt_text = clean(img.get('alt', '')).casefold() if img else ''
    category = ('Masszázs' if 'masszázs' in alt_text else 'Dominák' if 'domin' in alt_text else 'Szexpartner' if 'szexpartner' in alt_text else None)
    return {'id': identifier, 'nev': name, 'eletkor': age, 'testsuly': weight,
            'helyszin': location, 'telepules': city, 'nem_debrecen': city is not None and city.casefold() != 'debrecen',
            'kategoria': category, 'ma': today, 'kep': image,
            'adatlap': urljoin(page_url, link.get('href', '')), 'uj': False}


def get_count(soup):
    tag = soup.select_one('#listNumResultContainer')
    match = re.search(r'(\d+)', tag.get_text(' ', strip=True)) if tag else None
    return int(match.group(1)) if match else None


def inspect(soup):
    title = clean(soup.title.get_text(' ', strip=True)) if soup.title else '(nincs cím)'
    heading = soup.select_one('#listNumResultContainer')
    print('Oldal:', title, '|', clean(heading.get_text(' ', strip=True)) if heading else 'talalatszam nelkul')


def correct_county(soup):
    title = clean(soup.title.get_text(' ', strip=True)) if soup.title else ''
    h1 = [clean(x.get_text(' ', strip=True)) for x in soup.find_all('h1')]
    return COUNTY.casefold() in title.casefold() and any('hajdú-bihar megye lányok' in x.casefold() for x in h1)


def get_html(session):
    response = session.get(URL, timeout=30)
    response.raise_for_status()
    soup = BeautifulSoup(response.content, 'html.parser')
    inspect(soup)
    if correct_county(soup):
        return soup
    # A megyei menü valójában egy POST űrlapot küld, nem elegendő minden
    # környezetben a URL önmagában. Az oldalban szereplő űrlapot használjuk.
    form = soup.select_one('form input[name="incoming[county]"][value="Hajdú-Bihar"]')
    if form:
        form = form.find_parent('form')
    if form:
        payload = [(x.get('name'), x.get('value', '')) for x in form.select('input[name]')]
    else:
        payload = [('incoming[fvaroskerulet][]', city + '_') for city in CITIES]
        payload += [('tag_category', 'VIDÉK'), ('incoming[fneme]', 'Nő'), ('incoming[county]', COUNTY), ('search', '1')]
    print('Megyei POST-szures alkalmazasa:', COUNTY)

    from urllib.parse import urlencode

    kodolt_adatok = urlencode(
        payload,
        encoding="iso-8859-2"
    )

    response = session.post(
        URL,
        data=kodolt_adatok,
        timeout=30,
        headers={
            "Referer": URL,
            "Content-Type": "application/x-www-form-urlencoded"
        }
    )

    response.raise_for_status()
    soup = BeautifulSoup(response.content, 'html.parser')
    inspect(soup)
    return soup


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--html-file', help='Kizarolag helyi HTML teszt, halozat nelkul')
    args = parser.parse_args()
    if args.html_file:
        soup = BeautifulSoup(Path(args.html_file).read_text(encoding='utf-8'), 'html.parser')
    else:
        session = requests.Session()
        session.headers.update(HEADERS)
        soup = get_html(session)
    if not correct_county(soup):
        raise SystemExit('HIBA: nem a Hajdu-Bihar megyei listat kaptuk; a rossz.json valtozatlan!')
    expected = get_count(soup)
    if expected is None or expected < 1:
        raise SystemExit('HIBA: nincs hiteles talalatszam; a rossz.json valtozatlan!')
    cards = soup.select('#listPageListContent .listOuterDiv[data-memberthumb]')
    result_by_id = {}
    for card in cards:
        item = parse_card(card, URL)
        if item:
            # Egy szemely a kiemelt es a normal listaban is szerepelhet.
            # Az elso, teljesebb kartya elonyt elvez.
            if item['id'] not in result_by_id or sum(v is not None for v in item.values()) > sum(v is not None for v in result_by_id[item['id']].values()):
                result_by_id[item['id']] = item
    result = list(result_by_id.values())
    print(f'HTML-kartyak: {len(cards)}, egyedi azonositok: {len(result)}, kiirt talalatok: {expected}')
    # A mintaforras mind a 114 hirdetest tartalmazza. Ha az elo oldal kevesebbet ad,
    # az lehet JS/lazy-loading: ilyenkor tilos reszleges JSON-t felulirni.
    if len(result) < expected:
        raise SystemExit(f'HIBA: hianyos lista ({len(result)}/{expected}), JSON valtozatlan. A lapozast kulon kell vizsgalni.')
    if len(result) > expected * 1.2:
        raise SystemExit('HIBA: tul sok a listaelemek szama; JSON valtozatlan.')
    if sum(x['telepules'] is None for x in result) > len(result) * 0.2:
        raise SystemExit('HIBA: tul sok hianyzo helyszin; JSON valtozatlan.')
    previous_ids = set()
    if OUT.exists():
        previous = json.loads(OUT.read_text(encoding='utf-8'))
        if isinstance(previous.get('hirdetesek'), list) and previous['hirdetesek']:
            previous_ids = {str(item['id']) for item in previous['hirdetesek']}
    for item in result:
        item['uj'] = bool(previous_ids) and item['id'] not in previous_ids

    
        # Hirdetesek osszesitese telepulesenkent
    from collections import Counter

    telepulesek = Counter(
        item['telepules'] or 'Ismeretlen'
        for item in result
    )

    telepulesek = dict(
        sorted(
            telepulesek.items(),
            key=lambda x: (-x[1], x[0])
        )
    )

    
    output = {'forras': URL, 'megye': COUNTY,
              'frissitve': datetime.now(ZoneInfo('Europe/Budapest')).strftime('%Y.%m.%d. %H:%M'),
              'darab': len(result), 'uj_darab': sum(x['uj'] for x in result),
              'nem_debrecen_darab': sum(x['nem_debrecen'] for x in result),
              'telepulesek': telepulesek,
              'hirdetesek': result}
    OUT.write_text(json.dumps(output, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print('rossz.json elkeszult:', len(result), 'hirdetes, uj:', output['uj_darab'])


if __name__ == '__main__':
    main()
