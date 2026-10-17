"""Tests « Magasins près de moi » : base des magasins, GPS, adresse, distances, horaires, replis, liens drive.
Sert le dépôt en local ; les serveurs externes et la base des magasins sont simulés.
Usage : python3 tests/localisation.py   (contient aussi les outils communs aux autres tests)
"""
import json, math, os, random, re, socket, subprocess, sys, threading, time
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from functools import partial
from playwright.sync_api import sync_playwright

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.environ.get('RS_OUT', '/tmp/rayon-sur-tests')
os.makedirs(OUT, exist_ok=True)
FAIL = []
def check(cond, msg):
    print(('  ok  ' if cond else '  ÉCHEC ') + msg)
    if not cond: FAIL.append(msg)

# --- magasins simulés (même format que tools/build_stores.py)
RENNES = (48.1113, -1.6800); AVR = (48.6844, -1.3569)
STORES = [
    ['leclerc', 48.1000, -1.7000, 'E.Leclerc Cleunay', '12 rue de Lorient, Rennes', 'Mo-Sa 08:30-20:00'],
    ['leclerc', 48.0600, -1.6000, 'E.Leclerc Express', 'Chantepie', ''],
    ['carrefour', 48.1150, -1.6750, 'Carrefour City', '3 place Sainte-Anne, Rennes', 'Mo-Sa 08:00-21:00; Su 09:00-12:30'],
    ['lidl', 48.1300, -1.6500, 'Lidl', 'Rennes', 'Mo-Sa 08:30-20:00'],
    ['biocoop', 48.1050, -1.6900, 'Biocoop Scarabée', 'Rennes', 'Mo-Sa 09:00-19:30'],
    ['u', 48.0500, -1.7500, 'Super U', 'Bruz', ''],
    ['auchan', 48.2000, -1.8000, 'Auchan', 'Pacé', '24/7'],
    ['grandfrais', 48.0900, -1.6200, 'Grand Frais', 'Cesson-Sévigné', 'Mo-Sa 08:30-19:30; Su off'],
    ['leclerc', 48.6800, -1.3700, 'E.Leclerc Avranches', 'Saint-Martin-des-Champs', 'Mo-Sa 08:30-20:00'],
    ['carrefour', 48.6900, -1.3500, 'Carrefour Market Avranches', 'Avranches', 'Mo-Sa 08:30-19:30'],
]
TILES = {}
for r in STORES:
    TILES.setdefault(f'{math.floor(r[1] * 2)}_{math.floor(r[2] * 2)}', []).append(r)
INDEX = {'date': '2026-10-17', 'n': len(STORES), 'chains': {}, 'tiles': {k: len(v) for k, v in TILES.items()}}

COMMUNES = {
    'rennes': {'nom': 'Rennes', 'codesPostaux': ['35000', '35200', '35700'], 'centre': {'type': 'Point', 'coordinates': [-1.68, 48.1113]}, 'population': 225000},
    'avranches': {'nom': 'Avranches', 'codesPostaux': ['50300'], 'centre': {'type': 'Point', 'coordinates': [-1.3569, 48.6844]}, 'population': 10000},
}


def free_port():
    s = socket.socket(); s.bind(('127.0.0.1', 0)); p = s.getsockname()[1]; s.close(); return p


class Quiet(SimpleHTTPRequestHandler):
    def log_message(self, *a): pass


def serve():
    port = free_port()
    httpd = ThreadingHTTPServer(('127.0.0.1', port), partial(Quiet, directory=REPO))
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return httpd, f'http://127.0.0.1:{port}/'


LOG = []
def setup_routes(ctx, mode):
    """mode : dict d'options — tiles (bool), overpass ('ok'|'remark-then-ok'|'down'), geoapi (bool)"""
    def j(route, data, status=200):
        route.fulfill(status=status, body=json.dumps(data), headers={'content-type': 'application/json', 'access-control-allow-origin': '*'})

    def stores(route):
        url = route.request.url; LOG.append(url)
        if not mode.get('tiles', True): return route.fulfill(status=404, body='not found')
        m = re.search(r'/data/stores/([^/?]+)\.json', url)
        if not m: return route.fulfill(status=404, body='')
        k = m.group(1)
        if k == 'index': return j(route, INDEX)
        return j(route, TILES.get(k, [])) if k in TILES else route.fulfill(status=404, body='')
    ctx.route(re.compile(r'.*/data/stores/.*'), stores)

    ov_calls = {'n': 0}
    def overpass(route):
        url = route.request.url; LOG.append(url); ov_calls['n'] += 1
        m = mode.get('overpass', 'ok')
        if m == 'down': return route.fulfill(status=504, body='Gateway Timeout')
        if m == 'remark-then-ok' and 'private.coffee' in url:
            return j(route, {'elements': [], 'remark': 'runtime error: Query timed out in "query" at line 1 after 26 seconds.'})
        els = [{'type': 'node', 'id': i, 'lat': r[1], 'lon': r[2], 'tags': {'shop': 'supermarket', 'brand': {'leclerc': 'E.Leclerc', 'carrefour': 'Carrefour', 'lidl': 'Lidl', 'biocoop': 'Biocoop', 'u': 'Super U', 'auchan': 'Auchan', 'grandfrais': 'Grand Frais'}[r[0]], 'name': r[3], 'opening_hours': r[5]}} for i, r in enumerate(STORES)]
        els.append({'type': 'node', 'id': 999, 'lat': 48.112, 'lon': -1.679, 'tags': {'shop': 'convenience', 'name': 'Au Carrefour des Saveurs'}})
        return j(route, {'elements': els})
    ctx.route(re.compile(r'.*(overpass|maps\.mail\.ru).*'), overpass)

    def geoapi(route):
        url = route.request.url; LOG.append(url)
        if not mode.get('geoapi', True): return route.abort()
        if 'lat=' in url:
            lat = float(re.search(r'lat=([-\d.]+)', url).group(1))
            return j(route, [{'nom': 'Avranches' if lat > 48.5 else 'Rennes'}])
        if 'codePostal=' in url:
            cp = re.search(r'codePostal=(\d+)', url).group(1)
            return j(route, [c for c in COMMUNES.values() if cp in c['codesPostaux']])
        q = re.search(r'nom=([^&]+)', url).group(1).lower()
        return j(route, [c for k, c in COMMUNES.items() if k.startswith(q[:4])])
    ctx.route(re.compile(r'.*geo\.api\.gouv\.fr.*'), geoapi)
    def geopf(route):
        url = route.request.url; LOG.append(url)
        if '/reverse' in url:
            return j(route, {'features': [{'geometry': {'coordinates': [-1.68, 48.11]}, 'properties': {'city': 'Rennes'}}]})
        q = re.search(r'q=([^&]+)', url).group(1).lower()
        if 'rue' in q:
            return j(route, {'features': [{'geometry': {'coordinates': [-1.7005, 48.1005]}, 'properties': {'type': 'housenumber', 'label': '12 Rue de Lorient 35000 Rennes', 'name': '12 Rue de Lorient', 'city': 'Rennes', 'postcode': '35000'}},
                                          {'geometry': {'coordinates': [-1.35, 48.68]}, 'properties': {'type': 'street', 'label': 'Rue de Lorient 50300 Avranches', 'name': 'Rue de Lorient', 'city': 'Avranches', 'postcode': '50300'}}]})
        return j(route, {'features': [{'geometry': {'coordinates': [-1.345193, 48.677533]}, 'properties': {'type': 'municipality', 'label': 'Avranches', 'city': 'Avranches', 'name': 'Avranches', 'postcode': '50300'}}]})
    ctx.route(re.compile(r'.*data\.geopf\.fr.*'), geopf)
    ctx.route(re.compile(r'.*nominatim.*'), lambda r: j(r, [{'lat': '48.6844', 'lon': '-1.3569', 'display_name': 'Avranches, Manche'}]))
    # le reste d'internet : réponses vides
    ctx.route(re.compile(r'.*(openfoodfacts|economie\.gouv|google).*'), lambda r: j(r, {'products': [], 'count': 0, 'results': [], 'items': [], 'total_count': 0}))
    ctx.route(re.compile(r'.*(unpkg|jsdelivr|cdnjs).*'), lambda r: r.fulfill(status=404, body=''))   # scripts externes (lecteur de codes-barres) indisponibles
    return ov_calls


def new_page(b, base, *, geo=None, granted=True, mode=None, init=None):
    opts = {'viewport': {'width': 390, 'height': 844}, 'locale': 'fr-FR', 'timezone_id': 'Europe/Paris'}
    if geo: opts['geolocation'] = {'latitude': geo[0], 'longitude': geo[1], 'accuracy': 40}
    if granted: opts['permissions'] = ['geolocation']
    ctx = b.new_context(**opts)
    ov = setup_routes(ctx, mode or {})
    errs = []
    ls = {'rs2:profile': {'sel': ['milk', 'gluten'], 'traces': False, 'words': []}, 'rs2:geoAsked': 1}
    ls.update(init or {})
    ctx.add_init_script("""(() => { if (sessionStorage.getItem('__init')) return; sessionStorage.setItem('__init', '1');
      const d = %s; for (const k in d) localStorage.setItem(k, JSON.stringify(d[k])); })();""" % json.dumps(ls))
    page = ctx.new_page()
    page.on('pageerror', lambda e: errs.append(str(e)))
    page.on('console', lambda m: errs.append('console: ' + m.text) if m.type == 'error' and 'Failed to load resource' not in m.text else None)
    page.goto(base)
    return ctx, page, errs, ov


def wait_near(page, timeout=8000):
    page.wait_for_function("() => window.__RS && window.__RS.nearIds().length > 0", timeout=timeout)


def main():
    httpd, base = serve()
    with sync_playwright() as p:
        b = p.chromium.launch()

        print('1. Ouverture avec la position autorisée (Rennes)')
        ctx, page, errs, _ = new_page(b, base, geo=RENNES)
        wait_near(page)
        page.wait_for_timeout(600)
        st = page.evaluate("() => ({ store:__RS.S.store, ids:__RS.nearIds(), near:__RS.getNear() })")
        check(st['store'] == 'near', 'magasin « Près de moi » choisi d\'office')
        check(st['near']['label'] == 'Rennes', 'nom de la ville trouvé : ' + str(st['near']['label']))
        check(st['near']['r'] == 10, 'distance automatique 10 km : ' + str(st['near']['r']))
        check(st['ids'][:2] == ['carrefour', 'biocoop'], 'enseignes triées par distance : ' + ','.join(st['ids']))
        check('auchan' not in st['ids'], 'Auchan (13 km) hors des 10 km')
        check('u' in st['ids'], 'Super U (8,6 km) dans les 10 km')
        check(st['near']['stores']['leclerc']['n'] == 2, 'deux Leclerc à moins de 10 km')
        line = page.inner_text('#nearLine')
        check(page.is_visible('#nearLine') and line.startswith('Rennes · Carrefour, Biocoop'), 'ligne « près de moi » : ' + line.replace('\n', ' '))
        check('Près de moi (Rennes)' in page.inner_text('#store'), 'sélecteur : Près de moi (Rennes)')

        print('2. Fiche « Magasins près de moi »')
        page.click('#nearLine')
        page.wait_for_selector('#nearSheet[open]')
        page.wait_for_timeout(600)
        txt = page.inner_text('#nearSheet')
        check('Près de Rennes' in txt, 'titre de la position')
        check('E.Leclerc Cleunay' in txt and 'Itinéraire' in txt, 'magasin le plus proche et itinéraire')
        check(re.search(r'(Ouvert jusqu|Fermé)', txt) is not None, 'horaires affichés')
        check('2 magasins à moins de 10 km' in txt, 'nombre de magasins de l\'enseigne')
        page.screenshot(path=os.path.join(OUT, 'magasins.png'))

        print('3. Écarter une enseigne')
        page.click('#locList input[data-chain="lidl"]')
        ids = page.evaluate("() => __RS.nearIds()")
        check('lidl' not in ids, 'Lidl écarté de « Près de moi »')
        check(page.evaluate("() => JSON.parse(localStorage.getItem('rs2:loc')).off") == ['lidl'], 'choix enregistré')

        print('4. Distance 20 km')
        page.click('#radiusChips [data-r="20"]')
        page.wait_for_timeout(300)
        ids = page.evaluate("() => __RS.nearIds()")
        check('auchan' in ids, 'Auchan apparaît à 20 km')
        page.click('#radiusChips [data-r="0"]')
        page.wait_for_timeout(200)
        check('auchan' not in page.evaluate("() => __RS.nearIds()"), 'retour en automatique')
        page.click('#nearClose')
        check(not page.is_visible('#nearSheet'), 'fiche fermée')

        print('5. Déplacement à Avranches puis actualisation')
        ctx.set_geolocation({'latitude': AVR[0], 'longitude': AVR[1], 'accuracy': 30})
        page.click('#nearLine'); page.wait_for_selector('#nearSheet[open]')
        page.click('#locGps')
        page.wait_for_function("() => __RS.getNear().label === 'Avranches'", timeout=8000)
        st = page.evaluate("() => ({ ids:__RS.nearIds(), near:__RS.getNear() })")
        check(st['ids'] == ['carrefour', 'leclerc'], 'enseignes d\'Avranches : ' + ','.join(st['ids']))
        check(st['near']['r'] == 25, 'distance automatique élargie à 25 km (peu d\'enseignes) : ' + str(st['near']['r']))
        check('Avranches' in page.inner_text('#locWhere'), 'fiche mise à jour')
        page.click('#nearClose')
        check(not errs, 'aucune erreur JavaScript' + (': ' + '; '.join(errs[:3]) if errs else ''))
        ctx.close()

        print('6. Position refusée, puis ville avec suggestions')
        ctx, page, errs, _ = new_page(b, base, granted=False, init={'rs2:search': {'store': 'near', 'rayon': 'en:ice-creams-and-sorbets', 'ran': False}})
        page.wait_for_timeout(800)
        check(page.is_visible('#nearLine') and 'Position inconnue' in page.inner_text('#nearLine') and 'Choisir' in page.inner_text('#nearLine'), 'ligne d\'alerte quand aucune position')
        page.click('#nearLine'); page.wait_for_selector('#nearSheet[open]')
        page.wait_for_function("() => !document.querySelector('#locMsg').hidden && /bloquée|trouvé/.test(document.querySelector('#locMsg').textContent)", timeout=10000)
        msg = page.inner_text('#locMsg')
        check('adresse' in msg, 'aide affichée : ' + msg[:90])
        page.fill('#locCity', 'avran')
        page.wait_for_selector('#locSug button', timeout=4000)
        check('50300' in page.inner_text('#locSug'), 'suggestion Avranches (50300)')
        page.click('#locSug button')
        page.wait_for_function("() => __RS.nearIds().length === 2", timeout=8000)
        st = page.evaluate("() => ({ store:__RS.S.store, near:__RS.getNear(), loc:__RS.loc })")
        check(st['near']['src'] == 'city' and st['loc']['mode'] == 'city', 'ville enregistrée (mode ville)')
        check(st['store'] == 'near', 'magasin « Près de moi » actif')
        page.fill('#locCity', '35000'); page.press('#locCity', 'Enter')
        page.wait_for_function("() => __RS.getNear().label === 'Rennes'", timeout=8000)
        check(True, 'code postal 35000 → Rennes')
        page.click('#nearClose')
        check(not errs, 'aucune erreur JavaScript' + (': ' + '; '.join(errs[:3]) if errs else ''))
        ctx.close()

        print('6b. geo.api.gouv.fr en panne : géocodeur de l\'IGN')
        ctx, page, errs, _ = new_page(b, base, geo=RENNES, mode={'geoapi': False})
        wait_near(page)
        page.wait_for_function("() => __RS.getNear().label === 'Rennes'", timeout=8000)
        check(True, 'nom de la ville via l\'IGN')
        page.click('#nearLine'); page.wait_for_selector('#nearSheet[open]')
        page.fill('#locCity', 'avranches')
        page.wait_for_selector('#locSug button', timeout=5000)
        check('Avranches' in page.inner_text('#locSug'), 'suggestion via l\'IGN')
        check(not errs, 'aucune erreur JavaScript' + (': ' + '; '.join(errs[:3]) if errs else ''))
        ctx.close()

        print('7. Base des magasins indisponible : Overpass, 1er serveur en échec déguisé')
        ctx, page, errs, ov = new_page(b, base, geo=RENNES, mode={'tiles': False, 'overpass': 'remark-then-ok'})
        wait_near(page, 12000)
        ids = page.evaluate("() => __RS.nearIds()")
        check(ov['n'] >= 2, f'deuxième serveur Overpass utilisé ({ov["n"]} appels)')
        check(ids[:2] == ['carrefour', 'biocoop'], 'mêmes enseignes via Overpass : ' + ','.join(ids))
        check(page.evaluate("() => __RS.getNear().from") == 'osm', 'source : Overpass')
        check(not errs, 'aucune erreur JavaScript' + (': ' + '; '.join(errs[:3]) if errs else ''))
        ctx.close()

        print('8. Tout est en panne : message clair, pas de données perdues')
        ctx, page, errs, ov = new_page(b, base, geo=RENNES, mode={'tiles': False, 'overpass': 'down'})
        page.wait_for_timeout(2500)
        page.select_option('#store', 'near'); page.wait_for_selector('#nearSheet[open]')
        page.wait_for_function("() => /liste des magasins/.test(document.querySelector('#locMsg').textContent)", timeout=15000)
        check(True, 'message « liste des magasins n\'a pas pu être chargée »')
        check(page.evaluate("() => __RS.loc.okAt") > 0, 'position bien reçue (nouvel essai au prochain lancement)')
        ctx.close()

        print('9. Ancien format enregistré (v3.6)')
        old = {'lat': 48.11, 'lon': -1.68, 'label': 'ta position', 'at': int(time.time() * 1000) - 86400000 * 2,
               'stores': {'leclerc': {'name': 'E.Leclerc', 'dist': 2.1, 'lat': 48.1, 'lon': -1.7, 'n': 1}}}
        ctx, page, errs, _ = new_page(b, base, geo=RENNES, init={'rs2:near': old, 'rs2:search': {'store': 'near', 'rayon': 'en:ice-creams-and-sorbets', 'ran': False}})
        page.wait_for_function("() => Array.isArray(__RS.getNear().places)", timeout=8000)
        check(len(page.evaluate("() => __RS.nearIds()")) >= 5, 'ancien format remplacé par la nouvelle base')
        check(not errs, 'aucune erreur JavaScript' + (': ' + '; '.join(errs[:3]) if errs else ''))
        ctx.close()

        print('10. Choix manuel d\'une enseigne respecté par la mise à jour automatique')
        ctx, page, errs, _ = new_page(b, base, geo=RENNES)
        wait_near(page)
        page.select_option('#store', 'lidl')
        page.wait_for_timeout(300)
        page.evaluate("() => { const n = JSON.parse(localStorage.getItem('rs2:near')); }")
        ctx.set_geolocation({'latitude': AVR[0], 'longitude': AVR[1], 'accuracy': 30})
        page.wait_for_timeout(200)
        page.evaluate("() => { const n = __RS.getNear(); n.fixAt = Date.now() - 3600e3; }")
        # le cache de position de Chromium (5 min) remplace ici le temps passé hors de l'appli
        page.evaluate("() => { const g = navigator.geolocation.getCurrentPosition.bind(navigator.geolocation); navigator.geolocation.getCurrentPosition = (a, b, o) => g(a, b, Object.assign({}, o, { maximumAge:0 })); }")
        page.evaluate("() => document.dispatchEvent(new Event('visibilitychange'))")
        page.wait_for_function("() => __RS.getNear().label === 'Avranches'", timeout=8000)
        check(page.evaluate("() => __RS.S.store") == 'lidl', 'Lidl reste choisi après la mise à jour automatique')
        check(not errs, 'aucune erreur JavaScript' + (': ' + '; '.join(errs[:3]) if errs else ''))
        ctx.close()

        print('10b. Adresse complète, puis repli quand le GPS échoue')
        ctx, page, errs, _ = new_page(b, base, granted=False, init={'rs2:search': {'store': 'near', 'rayon': 'en:ice-creams-and-sorbets', 'ran': False}})
        page.wait_for_timeout(500)
        page.click('#nearLine'); page.wait_for_selector('#nearSheet[open]')
        page.wait_for_timeout(1500)
        page.fill('#locCity', '12 rue de lorient rennes')
        page.wait_for_selector('#locSug button', timeout=5000)
        check('12 Rue de Lorient' in page.inner_text('#locSug') and '35000 Rennes' in page.inner_text('#locSug'), 'suggestion d\'adresse : ' + page.inner_text('#locSug').replace('\n', ' | ')[:80])
        page.click('#locSug button >> nth=0')
        page.wait_for_function("() => __RS.getNear() && __RS.getNear().full === '12 Rue de Lorient 35000 Rennes'", timeout=8000)
        st = page.evaluate("() => ({ near:__RS.getNear(), loc:__RS.loc, ids:__RS.nearIds() })")
        check(st['near']['label'] == 'Rennes' and st['loc']['home']['full'] == '12 Rue de Lorient 35000 Rennes', 'adresse enregistrée, ville : Rennes')
        check(st['ids'][0] == 'leclerc', 'magasin le plus proche de l\'adresse : E.Leclerc (à 100 m) : ' + ','.join(st['ids'][:3]))
        check('Ton adresse' in page.inner_text('#locWhen') and page.is_visible('#homeRow'), 'fiche : « Ton adresse » et adresse enregistrée')
        check(not page.is_visible('#homeUse'), 'bouton « Utiliser » masqué quand l\'adresse est déjà utilisée')
        page.click('#locGps')
        page.wait_for_function("() => /adresse enregistrée/.test(document.querySelector('#locMsg').textContent)", timeout=10000)
        check(page.evaluate("() => __RS.getNear().src") == 'city', 'GPS refusé : l\'adresse reste utilisée')
        page.click('#nearClose')
        page.wait_for_timeout(300)
        saved = page.evaluate("() => ({ loc:localStorage.getItem('rs2:loc') })")
        check(not errs, 'aucune erreur JavaScript' + (': ' + '; '.join(errs[:3]) if errs else ''))
        ctx.close()
        # nouvelle session sans position : l'adresse sert d'office
        ctx, page, errs, _ = new_page(b, base, granted=False, init={'rs2:loc': {'auto': True, 'mode': 'gps', 'radius': 0, 'off': [], 'okAt': 0,
            'home': {'main': '12 Rue de Lorient', 'city': 'Rennes', 'full': '12 Rue de Lorient 35000 Rennes', 'kind': 'housenumber', 'lat': 48.1005, 'lon': -1.7005}}})
        page.wait_for_function("() => __RS.nearIds().length > 0", timeout=8000)
        check(page.evaluate("() => __RS.S.store") == 'near' and page.evaluate("() => __RS.getNear().label") == 'Rennes', 'sans GPS au démarrage : magasins autour de l\'adresse')
        check(not errs, 'aucune erreur JavaScript' + (': ' + '; '.join(errs[:3]) if errs else ''))
        ctx.close()

        print('10c. Stock au drive')
        shop = [{'code': '3017620422003', 'p': {'code': '3017620422003', 'product_name': 'Glace vanille', 'brands': 'Carte d\'Or', 'stores_tags': ['carrefour']}, 'done': False, 'at': 1}]
        ctx, page, errs, _ = new_page(b, base, geo=RENNES, init={'rs2:shop': shop, 'rs2:search': {'store': 'near', 'rayon': 'en:ice-creams-and-sorbets', 'ran': True}})
        wait_near(page)
        page.wait_for_selector('#results:not([hidden]) #list li .name', timeout=20000)
        page.click('#list li .name >> nth=0')
        page.wait_for_selector('#sheet[open] .drivebtn', timeout=8000)
        hrefs = page.eval_on_selector_all('#sheet .drivebtn .dmain', 'els => els.map(e => e.href)')
        txt = page.inner_text('#sheet .drives')
        check(len(hrefs) >= 2 and ('Voir le produit' in txt or 'Chercher' in txt), f'{len(hrefs)} liens vers les drives : ' + txt.replace('\n', ' | ')[:120])
        check(any('carrefour.fr/s?q=' in h for h in hrefs) or any('e.leclerc/recherche?q=' in h for h in hrefs), 'recherche directe sur le site de l\'enseigne')
        page.click('#sheetClose')
        sojade = {'code': '3273220020018', 'product_name': 'À la Grecque Greek Style Nature-Natural', 'brands': 'Sojade', 'stores_tags': ['biocoop']}
        ids = page.evaluate("p => __RS.linkChains(p)", sojade)
        check(ids[0] == 'biocoop' and 'lidl' not in ids, 'Sojade : Biocoop en premier, pas Lidl (sans drive, jamais vu) : ' + ','.join(ids))
        check(page.evaluate("p => __RS.driveUrl(p, 'biocoop')", sojade) == 'https://www.biocoop.fr/catalogsearch/result/?q=Sojade%20Grecque%20Nature', 'recherche Biocoop courte')
        check(page.evaluate("p => __RS.driveUrl(p, 'carrefour', true)", sojade) == 'https://www.carrefour.fr/s?q=Sojade', 'recherche de secours : la marque seule')
        page.click('nav [data-go="list"]'); page.wait_for_timeout(400)
        page.click('#whereList [data-drive="carrefour"]')
        page.wait_for_selector('#driveSheet[open]')
        dl = page.eval_on_selector_all('#driveList a.dmain', 'els => els.map(e => e.href)')
        check(page.inner_text('#driveTitle') == 'Ma liste chez Carrefour' and len(dl) == 1 and "carrefour.fr/s?q=3017620422003" in dl[0] and page.locator('#driveList .dalt').count() == 1 and 'Carte' in page.inner_text('#driveList .dalt'), 'Ma liste chez Carrefour : ' + (dl[0] if dl else '∅'))
        check('Vu dans l\'enseigne' in page.inner_text('#driveList'), 'disponibilité indiquée')
        page.screenshot(path=os.path.join(OUT, 'drive-liste.png'))
        check(not errs, 'aucune erreur JavaScript' + (': ' + '; '.join(errs[:3]) if errs else ''))
        ctx.close()

        print('11. Horaires d\'ouverture')
        ctx, page, errs, _ = new_page(b, base, geo=RENNES)
        cases = [
            ('Mo-Sa 08:30-20:00', '2026-10-17T10:00:00', 'Ouvert jusqu\'à 20 h'),     # samedi
            ('Mo-Sa 08:30-20:00', '2026-10-17T21:00:00', 'Fermé, ouvre lundi à 8 h 30'),
            ('Mo-Sa 08:30-20:00', '2026-10-18T10:00:00', 'Fermé, ouvre demain à 8 h 30'),  # dimanche
            ('Mo-Sa 08:00-21:00; Su 09:00-12:30', '2026-10-18T11:00:00', 'Ouvert jusqu\'à 12 h 30'),
            ('Mo-Fr 08:30-12:00,14:00-19:00; Sa 09:00-12:00', '2026-10-16T12:30:00', 'Fermé, ouvre à 14 h'),
            ('24/7', '2026-10-18T03:00:00', 'Ouvert 24 h/24'),
            ('Mo-Su 07:00-02:00', '2026-10-17T23:30:00', 'Ouvert jusqu\'à 2 h'),
            ('Mo-Su 07:00-02:00', '2026-10-18T01:00:00', 'Ouvert jusqu\'à 2 h'),
            ('Mo-Sa 09:00-19:00, Su 09:00-12:00', '2026-10-18T10:00:00', 'Ouvert jusqu\'à 12 h'),
            ('Mo,We,Fr 09:00-18:00', '2026-10-14T10:00:00', 'Ouvert jusqu\'à 18 h'),
            ('Mo,We,Fr 09:00-18:00', '2026-10-13T10:00:00', 'Fermé, ouvre demain à 9 h'),
            ('Mo-Sa 08:30-20:00; PH off', '2026-10-17T10:00:00', 'Ouvert jusqu\'à 20 h'),
            ('Mo-Sa 08:30-20:00; Su off', '2026-10-18T10:00:00', 'Fermé, ouvre demain à 8 h 30'),
            ('Jul-Aug Mo-Sa 09:00-20:00', '2026-10-17T10:00:00', None),
            ('sunrise-sunset', '2026-10-17T10:00:00', None),
            ('', '2026-10-17T10:00:00', None),
        ]
        for oh, at, want in cases:
            got = page.evaluate("([oh, at]) => { const o = __RS.ohStatus(oh, new Date(at)); return o ? o.text : null; }", [oh, at])
            check(got == want, f'{oh!r} à {at[11:16]} → {got!r}')
        print('12. Reconnaissance des enseignes OpenStreetMap')
        for tags, want in [({'brand': 'E.Leclerc'}, 'leclerc'), ({'name': 'E. Leclerc Drive'}, 'leclerc'), ({'brand': 'Carrefour Market'}, 'carrefour'),
                           ({'name': 'Au Carrefour des Saveurs'}, None), ({'brand': 'Super U'}, 'u'), ({'brand': 'U Express'}, 'u'), ({'brand': 'Utile'}, 'u'),
                           ({'name': 'Ulysse'}, None), ({'brand': 'Intermarché Super'}, 'intermarche'), ({'brand': "Monop'"}, 'monoprix'),
                           ({'brand': 'Petit Casino'}, 'casino'), ({'name': 'Coralie fleurs'}, None), ({'brand': 'Grand Frais'}, 'grandfrais'),
                           ({'brand': 'My Auchan'}, 'auchan'), ({'brand': 'Biocoop'}, 'biocoop'), ({'name': 'Picard'}, 'picard')]:
            got = page.evaluate("t => __RS.osmChain(t)", tags)
            check(got == want, f'{tags} → {got}')
        ctx.close()

        print('12b. Recherches envoyées aux sites des enseignes')
        ctx, page, errs, _ = new_page(b, base, geo=RENNES)
        page.wait_for_function("() => window.__RS", timeout=10000)
        for prod, want in [
            ({'product_name': 'À la Grecque Greek Style Nature-Natural', 'brands': 'Sojade'}, 'Sojade Grecque Nature'),
            ({'product_name': 'Râpé Gran Vegiano', 'brands': 'Nurishh'}, 'Nurishh Râpé Gran'),
            ({'product_name': 'HERTA Lardons fumés conservation sans nitrite - 2x75g', 'brands': 'Herta'}, 'Herta Lardons fumés'),
            ({'product_name': 'Lait demi-écrémé UHT 1L', 'brands': 'Lactel,Lactalis'}, 'Lactel Lait demi-écrémé'),
            ({'product_name': 'Spaghetti n°5 - 500 g', 'brands': 'Barilla'}, 'Barilla Spaghetti'),
            ({'product_name': 'Sauce tomate basilic (bio)', 'brands': ''}, 'Sauce tomate basilic'),
            ({'product_name': 'BN - Casse Croute Biscuits, 375g', 'brands': 'BN'}, 'BN Casse Croute'),
            ({'product_name': 'Thé - Biscuits', 'brands': 'Lu'}, 'Lu Thé'),
            ({'product_name': 'Almond Drink Sugar-Free', 'brands': 'Vemondo'}, 'Vemondo Almond Drink'),
            ({'product_name': 'BjORG AMANDE ALMOND SANS SUCRE- NO SUGAR', 'brands': 'Bjorg'}, 'Bjorg AMANDE SUCRE'),
            ({'product_name': 'Moutarde de Dijon', 'brands': 'CMI (Carrefour Marchandises Internationales)'}, 'Carrefour Moutarde Dijon'),
            ({'product_name': 'Twist Pêche 0.0', 'brands': 'TOURTEL Tourtel Twist Tourtel'}, 'TOURTEL Twist Pêche'),
            ({'product_name': 'Nutella', 'brands': 'Nutella'}, 'Nutella'),
            ({'product_name': "Menguy's Peanut 100%", 'brands': "menguy's"}, "menguy's Peanut"),
        ]:
            got = page.evaluate("p => __RS.driveTerms(Object.assign({ code:'1' }, p))", prod)
            check(got == want, f"{prod['product_name']!r} → {got!r}")
        check(not errs, 'aucune erreur JavaScript' + (': ' + '; '.join(errs[:3]) if errs else ''))
        ctx.close()

        print('13. Ma liste : où faire ses courses, avec horaires')
        shop = [{'code': '3017620422003', 'p': {'code': '3017620422003', 'product_name': 'Glace vanille', 'brands': 'Carte d\'Or', 'stores_tags': ['carrefour']}, 'done': False, 'at': 1}]
        ctx, page, errs, _ = new_page(b, base, geo=RENNES, init={'rs2:shop': shop})
        wait_near(page)
        page.click('nav [data-go="list"]')
        page.wait_for_timeout(500)
        txt = page.inner_text('#whereBox')
        check('Carrefour' in txt and 'Le plus proche' in txt, 'enseignes proches dans « Où faire tes courses »')
        check('Modifier mes magasins' in txt, 'bouton pour gérer ses magasins')
        check('Lidl' in txt or 'Biocoop' in txt, 'autres enseignes proches listées')
        page.screenshot(path=os.path.join(OUT, 'ma-liste.png'), full_page=True)
        page.click('nav [data-go="search"]')
        page.screenshot(path=os.path.join(OUT, 'recherche.png'))
        page.click('nav [data-go="profile"]')
        check('enseignes près de Rennes' in page.inner_text('#profNear'), 'Profil : ' + page.inner_text('#profNear').replace('\n', ' '))
        check(not errs, 'aucune erreur JavaScript' + (': ' + '; '.join(errs[:3]) if errs else ''))
        ctx.close()
        b.close()
    httpd.shutdown()
    print('\n' + ('TOUT EST OK' if not FAIL else f'{len(FAIL)} ÉCHEC(S)'))
    sys.exit(1 if FAIL else 0)


if __name__ == '__main__':
    main()
