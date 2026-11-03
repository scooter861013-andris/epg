import argparse
import html
import json
import re
from datetime import datetime
from pathlib import Path
from urllib.parse import urljoin, urlparse, urldefrag
from zoneinfo import ZoneInfo

import requests
from bs4 import BeautifulSoup

DEFAULT_URL = 'https://rosszlanyok.hu/varos-debrecen-lanyok'
OUT = Path('rossz.json')
HEADERS = {'User-Agent': 'Mozilla/5.0 (compatible; PersonalListReader/1.0)'}


def clean(s):
    return ' '.join(str(s or '').split())


def tooltip_text(tag):
    raw = tag.get('onmouseover', '') if tag else ''
    m = re.search(r"myToolTip\(\s*'((?:\\.|[^'\\])*)'", raw, re.S)
    if not m:
        return ''
    markup = html.unescape(m.group(1).replace("\\'", "'").replace('\\"', '"'))
    soup = BeautifulSoup(markup, 'html.parser')
    return '\n'.join(clean(t) for t in soup.stripped_strings)


def parse_card(card, page_url):
    member_id = clean(card.get('data-memberthumb', ''))
    name_tag = card.select_one('.nevToShowOnList .nev') or card.select_one('.nev')
    name_raw = clean(name_tag.get_text(' ', strip=True)) if name_tag else ''
    m = re.fullmatch(r'(.*?)\s*\((\d+)\)', name_raw)
    name, age = (m.group(1).strip(), int(m.group(2))) if m else (name_raw, None)
    a = card.select_one('a.onExternalAdvThumbLink')
    if not member_id or not name or not a:
        return None
    description = tooltip_text(a)
    img = card.select_one('img.listTagImage')
    img_rel = (img.get('data-src') or img.get('src') or '') if img else ''
    img_url = urljoin(page_url, img_rel) if img_rel and 'spacer.gif' not in img_rel else None
    link = urljoin(page_url, a.get('href', ''))
    lines = description.split('\n')
    location = next((x for x in lines if re.search(r'\bDebrecen\b', x, re.I)), None)
    # Az oldal részletes helyadatát csak akkor tüntetjük fel, ha ténylegesen benne van a listában.
    if location:
        location = re.split(r'\s+\d{1,2}\+?\s*éves', location)[0].strip(' ,')
    weight = None
    match = re.search(r'\b\d{1,2}\+?\s*éves\b[^\n]*?\b\d{2,3}\s*cm\s*,\s*(\d{2,3}\+?)\s*kg\b', description, re.I)
    if match:
        weight = match.group(1) + ' kg'
    today = None
    match = re.search(r'Ma:\s*([^\n]+)', description, re.I)
    if match:
        today = clean(match.group(1))
    alt = clean(img.get('alt', '')) if img else ''
    category = ('Masszázs' if 'masszázs' in alt.lower() else
                'Dominák' if 'domin' in alt.lower() else
                'Szexpartner' if 'szexpartner' in alt.lower() else None)
    return {
        'id': member_id, 'nev': name, 'eletkor': age, 'testsuly': weight,
        'helyszin': location, 'kategoria': category, 'ma': today,
        'kep': img_url, 'adatlap': link, 'uj': False,
    }


def pagination_links(soup, current_url, seed_url):
    seed_path = urlparse(seed_url).path.rstrip('/')
    origin = urlparse(seed_url).netloc
    urls = set()
    for a in soup.select('a[href]'):
        href = a.get('href', '').strip()
        if not href or href.startswith(('#', 'javascript:', 'mailto:')):
            continue
        u = urldefrag(urljoin(current_url, href)).url
        p = urlparse(u)
        if p.netloc != origin:
            continue
        label = clean(a.get_text(' ', strip=True)).lower()
        cls = ' '.join(a.get('class', [])).lower()
        # Csak a listázás oldalszámozó linkjei, nem az adatlapok.
        is_page = ('page' in p.query.lower() or 'oldal' in p.query.lower() or
                   re.search(r'\b(pager|pagination|lapozo)\b', cls) or
                   label in ('következő', 'tovább', 'next', '»', '›') or label.isdigit())
        same_list = (p.path.rstrip('/') == seed_path or
                     p.path.rstrip('/').startswith(seed_path + '/'))
        if same_list and is_page and u != current_url:
            urls.add(u)
    return urls


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--url', default=DEFAULT_URL)
    parser.add_argument('--max-pages', type=int, default=30)
    args = parser.parse_args()
    if not args.url.startswith('https://'):
        raise SystemExit('HTTPS cím szükséges.')
    old = {}
    if OUT.exists():
        old = json.loads(OUT.read_text(encoding='utf-8'))
    had_previous = isinstance(old.get('rossz'), list) and len(old['rossz']) > 0
    previous_ids = {str(x['id']) for x in old.get('rossz', [])} if had_previous else set()

    session = requests.Session()
    session.headers.update(HEADERS)
    queue, visited, all_cards = [args.url], set(), {}
    while queue:
        url = queue.pop(0)
        if url in visited:
            continue
        if len(visited) >= args.max_pages:
            raise SystemExit(f'Elértük az oldalkorlátot ({args.max_pages}); nem írjuk felül a JSON-t.')
        response = session.get(url, timeout=25)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        cards = soup.select('.listOuterDiv[data-memberthumb]')
        if not cards:
            raise SystemExit(f'Nincsenek felismerhető hirdetések ezen az oldalon: {url}; JSON változatlan.')
        for card in cards:
            item = parse_card(card, url)
            if item:
                all_cards[item['id']] = item
        visited.add(url)
        for nxt in sorted(pagination_links(soup, url, args.url)):
            if nxt not in visited and nxt not in queue:
                queue.append(nxt)
        print(f'Oldal {len(visited)}: {url} / {len(cards)} kártya / összesen {len(all_cards)} egyedi')

    if not all_cards:
        raise SystemExit('Üres eredmény, JSON változatlan.')
    if had_previous and len(all_cards) < len(previous_ids) * 0.65:
        raise SystemExit('Gyanúsan kevés eredmény az előző futáshoz képest; JSON változatlan.')
    result = list(all_cards.values())
    for item in result:
        item['uj'] = had_previous and item['id'] not in previous_ids
    timestamp = datetime.now(ZoneInfo('Europe/Budapest')).strftime('%Y.%m.%d. %H:%M')
    output = {
        'forras': args.url,
        'frissitve': timestamp,
        'darab': len(result),
        'uj_darab': sum(item['uj'] for item in result),
        'oldalak': len(visited),
        'megjegyzes': 'A teljes lista csak akkor garantálható, ha az oldal összes lapozási hivatkozása elérhető a HTML-ben.',
        'rossz': result,
    }
    OUT.write_text(json.dumps(output, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(f'JSON elkészült: {len(result)} hirdetés, ebből {output["uj_darab"]} új.')

if __name__ == '__main__':
    main()
