import argparse
import html
import json
import re
from datetime import datetime
from pathlib import Path
from urllib.parse import urljoin, urlparse, urldefrag, parse_qs
from zoneinfo import ZoneInfo

import requests
from bs4 import BeautifulSoup

DEFAULT_URL = 'https://rosszlanyok.hu/rosszlanyok.php?pid=szexpartner-lista&htext=73'
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
    # A tooltipben a kategória után jellemzően a helyszín következik.
    # Nem kényszerítjük Debrecenre: például Hajdúszoboszló is megmarad.
    location = None
    for idx, line in enumerate(lines[:-1]):
        if re.search(r'(szexpartner|masszázs|dominák)', line, re.I):
            candidate = clean(lines[idx + 1]).strip(' ,')
            if candidate and not re.search(r'(éves|cm|kg|Ma:|Holnap:)', candidate, re.I):
                location = candidate
                break
    if not location:
        # Alternatívaként a kép alt szövegéből keressük a települést.
        alt_text = clean(img.get('alt', '')) if img else ''
        pattern = re.escape(name) + r'\s+(.+?)\s+(?:szexpartner|masszázs|dominák)\s+lányok'
        location_match = re.search(pattern, alt_text, re.I)
        if location_match:
            location = clean(location_match.group(1))
    city = location.split(',')[0].strip() if location else None
    other_city = bool(city and city.casefold() not in ('debrecen',))
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
        'helyszin': location, 'telepules': city, 'nem_debrecen': other_city,
        'kategoria': category, 'ma': today,
        'kep': img_url, 'adatlap': link, 'uj': False,
    }


def pagination_links(soup, current_url, seed_url):
    """Csak azonos megyei listára vezető oldallapozó linkeket követ."""
    origin = urlparse(seed_url).netloc
    seed_params = parse_qs(urlparse(seed_url).query)
    urls = set()
    for a in soup.select('a[href]'):
        href = a.get('href', '').strip()
        if not href or href.startswith(('#', 'javascript:', 'mailto:')):
            continue
        u = urldefrag(urljoin(current_url, href)).url
        parsed = urlparse(u)
        if parsed.netloc != origin or parsed.path != urlparse(seed_url).path:
            continue
        params = parse_qs(parsed.query)
        if params.get('pid') != seed_params.get('pid') or params.get('htext') != seed_params.get('htext'):
            continue
        label = clean(a.get_text(' ', strip=True)).casefold()
        cls = ' '.join(a.get('class', [])).casefold()
        has_page_param = any(k.lower() in ('page', 'oldal', 'pageno', 'start', 'offset', 'lap') for k in params)
        page_link = has_page_param or any(z in cls for z in ('page', 'lapozo', 'pagination')) or label in ('következő', 'tovább', 'next', '»', '›')
        if page_link and u != current_url:
            urls.add(u)
    return urls


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--url', default=DEFAULT_URL)
    parser.add_argument('--max-pages', type=int, default=100)
    args = parser.parse_args()
    if not args.url.startswith('https://'):
        raise SystemExit('HTTPS cím szükséges.')
    old = {}
    if OUT.exists():
        old = json.loads(OUT.read_text(encoding='utf-8'))
    had_previous = isinstance(old.get('hirdetesek'), list) and len(old['hirdetesek']) > 0
    previous_ids = {str(x['id']) for x in old.get('hirdetesek', [])} if had_previous else set()

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
    # Biztonsági ellenőrzés: a megyei URL néha alapértelmezett (budapesti)
    # listát ad vissza. Ilyenkor nem írjuk felül a jól működő JSON-t.
    budapest_count = sum(bool(re.search(r'\bBudapest\b', x.get('helyszin') or '', re.I)) for x in all_cards.values())
    if budapest_count >= 3 and budapest_count > len(all_cards) * 0.25:
        raise SystemExit(f'Hibás megyei szűrés: {budapest_count}/{len(all_cards)} budapesti találat; JSON változatlan.')
    unknown_count = sum(x['telepules'] is None for x in all_cards.values())
    if unknown_count > len(all_cards) * 0.5:
        raise SystemExit(f'Túl sok hiányzó település: {unknown_count}/{len(all_cards)}; JSON változatlan.')
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
        'nem_debrecen_darab': sum(x['nem_debrecen'] for x in result),
        'megjegyzes': 'Csak a HTML-ben elérhető lapozást járja be. JavaScriptből betöltött további találatok külön ellenőrzést igényelnek.',
        'hirdetesek': result,
    }
    OUT.write_text(json.dumps(output, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(f'JSON elkészült: {len(result)} hirdetés, ebből {output["uj_darab"]} új.')

if __name__ == '__main__':
    main()
