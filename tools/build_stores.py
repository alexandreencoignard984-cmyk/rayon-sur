#!/usr/bin/env python3
"""Construit data/stores/ : les magasins des enseignes connues de Rayon sûr, partout en France.

Source : OpenStreetMap, © les contributeurs d'OpenStreetMap, licence ODbL. De préférence l'extrait
France de Geofabrik, filtré avec osmium (rapide et fiable) ; sinon l'API Overpass, carré par carré.
Une fois par semaine, au lieu d'une requête par utilisateur : l'appli lit ensuite des petites tuiles
de 0,5° sur GitHub Pages, sans dépendre des serveurs de cartes.

Sortie :
  data/stores/index.json      date, nombre de magasins par tuile et par enseigne
  data/stores/<la>_<lo>.json  [[enseigne, lat, lon, nom, adresse, horaires, site], ...]
                              avec la = floor(lat * 2), lo = floor(lon * 2)

Si un carré n'obtient aucune réponse, ses tuiles de la semaine précédente sont gardées.
Usage : python3 tools/build_stores.py                       (Overpass)
        python3 tools/build_stores.py magasins.osm.pbf ...   (extraits déjà filtrés par osmium tags-filter)
        python3 tools/build_stores.py overpass.json
"""
import datetime, json, math, os, re, shutil, sys, time, urllib.parse, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'data', 'stores')
SERVERS = [
    'https://overpass.private.coffee/api/interpreter',
    'https://overpass-api.de/api/interpreter',
    'https://maps.mail.ru/osm/tools/overpass/api/interpreter',
]
SHOPS = 'supermarket|convenience|frozen_food|greengrocer|organic|health_food|department_store|general|deli|wholesale'
# filtre large côté serveur, tri exact ensuite avec CHAINS
LOOSE = 'leclerc|carrefour|auchan|intermarch|super u|hyper u|u express|march. u|^u$|utile|lidl|aldi|monop|casino|franprix|cora|netto|biocoop|picard|grand frais'
# enseigne de l'appli : lue dans la marque (brand), sinon dans le nom
CHAINS = [
    ('leclerc', r'\b(e\.?\s?)?leclerc\b'),
    ('carrefour', r'^carrefour\b'),
    ('auchan', r'\bauchan\b'),
    ('intermarche', r'^interm(arch|arc)'),
    ('u', r'^((super|hyper|march[ée])\s+u|u\s+express|utile|u)\b(?!\w)'),
    ('lidl', r'^lidl\b'),
    ('aldi', r'^aldi\b'),
    ('monoprix', r"^monop(rix\b|'|’|\b)"),
    ('casino', r'^(petit\s+|g[ée]ant\s+|le\s+petit\s+)?casino\b'),
    ('franprix', r'^franprix\b'),
    ('cora', r'^cora\b'),
    ('netto', r'^netto\b'),
    ('biocoop', r'^biocoop\b'),
    ('picard', r'^picard\b'),
    ('grandfrais', r'^grand\s+frais\b'),
]
CHAINS = [(cid, re.compile(rx, re.I)) for cid, rx in CHAINS]
# ce ne sont pas des magasins où l'on fait ses courses
SKIP_NAME = re.compile(r'\b(station|carburant|lavage|location|voyages?|optique|drive pi[ée]ton|relais|casiers?|consignes?|locker)\b', re.I)
T0 = time.time()


def log(*a):
    print(f'[{time.time() - T0:6.1f}s]', *a, flush=True)


def boxes():
    """France découpée en carrés (multiples de 0,5° : une tuile appartient à un seul carré), puis l'outre-mer."""
    out, lat = [], 41.0
    while lat < 51.5:
        lon = -5.5
        while lon < 10.0:
            out.append((lat, lon, lat + 1.5, lon + 2.5, True))
            lon += 2.5
        lat += 1.5
    out += [(15.8, -61.9, 16.6, -61.0, False), (14.3, -61.3, 14.95, -60.75, False), (2.0, -54.7, 5.9, -51.5, False),
            (-21.45, 55.15, -20.85, 55.9, False), (-13.05, 44.95, -12.6, 45.35, False)]
    return out


def query(box):
    s, w, n, e, fr = box
    sel = f'["shop"~"^({SHOPS})$"]'
    area = '(area.fr)' if fr else ''
    bb = f'({s},{w},{n},{e})'
    return ('[out:json][timeout:180];' + ('area(id:3602202162)->.fr;' if fr else '') + '('
            f'nwr{sel}["brand"~"{LOOSE}",i]{area}{bb};'
            f'nwr{sel}["name"~"{LOOSE}",i]{area}{bb};);out center tags;')


def fetch_box(box, order):
    data = urllib.parse.urlencode({'data': query(box)}).encode()
    for attempt in range(2):
        for url in order:
            try:
                req = urllib.request.Request(url, data=data, headers={'User-Agent': 'rayon-sur/1.0 (https://github.com/alexandreencoignard984-cmyk/rayon-sur)'})
                with urllib.request.urlopen(req, timeout=150) as r:
                    j = json.loads(r.read())
                remark = (j.get('remark') or '').lower()
                if 'error' in remark or 'timed out' in remark or not isinstance(j.get('elements'), list):
                    raise RuntimeError('réponse incomplète : ' + remark[:120])
                return j['elements'], url
            except Exception as e:
                log(f'  {box[:4]} {url.split("/")[2]} : {str(e)[:160]}')
                time.sleep(5)
        time.sleep(30)
    return None, None


def fetch():
    """Renvoie (éléments, carrés en échec)."""
    els, failed, order, bx = [], [], list(SERVERS), boxes()
    for i, box in enumerate(bx):
        got, url = fetch_box(box, order)
        if got is None:
            failed.append(box)
            continue
        if url != order[0]:   # le serveur qui répond passe en tête
            order.remove(url)
            order.insert(0, url)
        els += got
        log(f'carré {i + 1}/{len(bx)} {box[:4]} : {len(got)} éléments ({url.split("/")[2]})')
        time.sleep(1)
    return els, failed


KEEP = ('shop', 'brand', 'name', 'addr:housenumber', 'addr:street', 'addr:city', 'opening_hours', 'website', 'contact:website')


def from_pbf(paths):
    """Magasins des extraits OpenStreetMap filtrés (points et bâtiments, centre des bâtiments)."""
    import osmium

    class Shops(osmium.SimpleHandler):
        def __init__(self):
            super().__init__()
            self.out = []

        def keep(self, tags, lat, lon):
            t = {k: tags.get(k) for k in KEEP if tags.get(k)}
            if (t.get('brand') or t.get('name')) and re.search(LOOSE.replace('^u$', r'^u\b'), (t.get('brand') or '') + ' | ' + (t.get('name') or ''), re.I):
                self.out.append({'lat': lat, 'lon': lon, 'tags': t})

        def node(self, n):
            if 'shop' in n.tags and n.location.valid():
                self.keep(n.tags, n.location.lat, n.location.lon)

        def way(self, w):
            if 'shop' not in w.tags:
                return
            pts = [(nd.location.lat, nd.location.lon) for nd in w.nodes if nd.location.valid()]
            if pts:
                self.keep(w.tags, sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts))

    h = Shops()
    for p in paths:
        log('Lecture de', p)
        h.apply_file(p, locations=True)
    log(f'{len(h.out)} magasins candidats dans les extraits')
    return h.out


def in_box(tile_key, box):
    a, b = (int(x) for x in tile_key.split('_'))
    lat, lon = a / 2 + 0.25, b / 2 + 0.25
    return box[0] <= lat < box[2] and box[1] <= lon < box[3]


def chain_of(tags):
    for key in ('brand', 'name'):
        v = (tags.get(key) or '').strip()
        if not v:
            continue
        for cid, rx in CHAINS:
            if rx.search(v):
                return cid
    return None


def main():
    failed = []
    args = sys.argv[1:]
    if args and all(a.endswith(('.pbf', '.osm')) for a in args):
        els = from_pbf(args)
    elif args:
        els = json.load(open(args[0], encoding='utf-8')).get('elements') or []
    else:
        els, failed = fetch()
    tiles, seen = {}, set()
    for el in els:
        t = el.get('tags') or {}
        cid = chain_of(t)
        if not cid:
            continue
        name = (t.get('name') or t.get('brand') or '').strip()
        if SKIP_NAME.search(name):
            continue
        lat = el.get('lat', (el.get('center') or {}).get('lat'))
        lon = el.get('lon', (el.get('center') or {}).get('lon'))
        if lat is None or lon is None:
            continue
        lat, lon = round(lat, 5), round(lon, 5)
        key = (cid, round(lat, 3), round(lon, 3))  # un même magasin dessiné deux fois (point + bâtiment)
        if key in seen:
            continue
        seen.add(key)
        street = ' '.join(x for x in (t.get('addr:housenumber'), t.get('addr:street')) if x).strip()
        city = (t.get('addr:city') or '').strip()
        addr = ', '.join(x for x in (street, city) if x)
        oh = (t.get('opening_hours') or '').strip()[:160]
        web = (t.get('website') or t.get('contact:website') or '').strip()
        web = web[:160] if web.startswith(('http://', 'https://')) else ''
        tk = f'{math.floor(lat * 2)}_{math.floor(lon * 2)}'
        tiles.setdefault(tk, []).append([cid, lat, lon, name[:60], addr[:80], oh, web])
    # carrés sans réponse : on reprend leurs tuiles de la semaine précédente
    kept = 0
    if failed and os.path.isdir(OUT):
        for f in os.listdir(OUT):
            k = f[:-5]
            if f == 'index.json' or not f.endswith('.json') or k in tiles:
                continue
            if any(in_box(k, b) for b in failed):
                tiles[k] = json.load(open(os.path.join(OUT, f), encoding='utf-8'))
                kept += 1
    chains = {}
    for rows in tiles.values():
        for r in rows:
            chains[r[0]] = chains.get(r[0], 0) + 1
    total = sum(chains.values())
    log(f'{total} magasins, {len(tiles)} tuiles ({kept} reprises), {len(failed)} carrés en échec', chains)
    if total < int(os.environ.get('MIN_STORES', 10000)):
        log('Trop peu de magasins : on garde les fichiers existants.')
        return 0
    tmp = OUT + '.tmp'
    shutil.rmtree(tmp, ignore_errors=True)
    os.makedirs(tmp)
    for tk, rows in tiles.items():
        rows.sort(key=lambda r: (r[1], r[2]))
        with open(os.path.join(tmp, tk + '.json'), 'w', encoding='utf-8') as f:
            json.dump(rows, f, ensure_ascii=False, separators=(',', ':'))
    index = {'date': datetime.date.today().isoformat(), 'n': total, 'chains': chains,
             'tiles': {k: len(v) for k, v in sorted(tiles.items())},
             'source': "© les contributeurs d'OpenStreetMap (ODbL)"}
    with open(os.path.join(tmp, 'index.json'), 'w', encoding='utf-8') as f:
        json.dump(index, f, ensure_ascii=False, separators=(',', ':'))
    shutil.rmtree(OUT, ignore_errors=True)
    os.rename(tmp, OUT)
    log('Écrit dans', OUT)
    return 0


if __name__ == '__main__':
    sys.exit(main())
