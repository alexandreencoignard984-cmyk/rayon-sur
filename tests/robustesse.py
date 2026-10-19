"""Robustesse : l'appli doit démarrer et rester utilisable même avec des données enregistrées abîmées,
sans réseau, ou quand on touche un peu tout au hasard. Toute erreur JavaScript fait échouer le test.
Usage : python3 tests/robustesse.py [nombre de clics au hasard, 150 par défaut]
"""
import json, os, random, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from localisation import serve, setup_routes, check, FAIL, RENNES
from playwright.sync_api import sync_playwright

PROFILE = {'sel': ['milk', 'gluten'], 'traces': False, 'words': ['palme']}
# valeurs abîmées, génériques puis propres à chaque clé
JUNK = ['null', '"texte"', '[]', '{}', '[null,1,"x"]', '{']
SPECIFIC = {
    'rs2:profile': [{'sel': 'milk'}, {'sel': [1, None, 'milk'], 'words': 'palme', 'traces': 'oui'}, {'words': [1, None, {}]}],
    'rs2:search': [{'nutri': 'z', 'sort': 'zz', 'rayon': 5, 'store': None, 'nova': 'x', 'terms': 12, 'ran': True},
                   {'store': 'near', 'ran': True}, {'rayon': 'en:inconnu', 'ran': True},
                   {'lastTerms': 5, 'lastRayon': 'en:inconnu', 'ran': True}, {'lastTerms': 'nutella', 'lastRayon': '', 'ran': True}],
    'rs2:favs': [{'1': None}, {'2': {'p': None}}, {'3': {'p': 'x'}}, {'4': {'p': {'code': 4}}}],
    'rs2:shop': [[{'code': 1}], [None, 'x', {'p': {}}], [{'code': 'a', 'p': {'product_name': 5, 'brands': ['x']}, 'done': 'oui'}]],
    'rs2:history': [[{'code': 1}], [{'code': 'b', 'p': None}], [{'code': 'c', 'p': {'labels_tags': 'en:vegan', 'stores_tags': 'lidl'}}]],
    'rs2:recipes': [[{'id': 1}], [{'id': 'm1', 'n': 'Test', 'i': 'spaghetti'}], [{'id': 'm2', 'n': 'Test', 'i': [['inconnu'], ['spaghetti']]}]],
    'rs2:near': [{'stores': {'leclerc': {}}}, {'stores': {'leclerc': {'dist': 'x'}}, 'places': [[1]]},
                 {'lat': 48.1, 'lon': -1.6, 'stores': {}, 'places': [['leclerc', 'a', None, 1, 2, 3]], 'cnt': 'x', 'r': 'x'},
                 {'lat': 48.1, 'lon': -1.6, 'label': 'ta position', 'at': 1, 'stores': {'carrefour': {'name': 'C', 'dist': 1.2, 'lat': 48.11, 'lon': -1.6}}}],
    'rs2:loc': [{'off': 'lidl', 'radius': 'x', 'home': {'lat': 'a'}}, {'mode': 'city', 'home': None}, {'home': 'x', 'mode': 'city'},
                {'mode': 'city', 'home': {'main': 'Rennes', 'city': 'Rennes', 'full': 'Rennes', 'kind': 'municipality', 'lat': 48.11, 'lon': -1.68}}],
    'rs2:drivetest': [{'items': [{}], 'res': {}}, {'items': 'x', 'res': 1}, {'v': 1, 'at': 1, 'chains': ['carrefour'], 'items': [{'p': {'code': '1'}, 'chains': ['carrefour'], 'seen': []}], 'res': {'1|carrefour': 'ok'}}],
    'rs2:theme': ['"violet"'],
}


def run_case(b, base, key, raw, errs_out):
    ctx = b.new_context(viewport={'width': 390, 'height': 844}, locale='fr-FR', geolocation={'latitude': RENNES[0], 'longitude': RENNES[1]}, permissions=['geolocation'])
    setup_routes(ctx, {})
    store = {'rs2:profile': json.dumps(PROFILE), 'rs2:geoAsked': '1', key: raw}
    ctx.add_init_script("""(() => { try { if (sessionStorage.getItem('__init')) return; sessionStorage.setItem('__init', '1');
      const d = %s; for (const k in d) localStorage.setItem(k, d[k]); } catch (e) {} })();""" % json.dumps(store))
    page = ctx.new_page()
    errs = []
    page.on('pageerror', lambda e: errs.append(str(e).split('\n')[0]))
    page.on('dialog', lambda d: d.accept())
    try:
        page.goto(base)
        page.wait_for_timeout(500)
        if page.is_visible('#onboard'):            # profil illisible : l'appli repart de l'écran de bienvenue
            page.click('#obSkip', timeout=5000)
        for tab in ['recipes', 'scan', 'list', 'profile', 'search']:
            page.click(f'nav [data-go="{tab}"]', timeout=5000)
            page.wait_for_timeout(80)
        page.click('#homeGrid .tile >> nth=0', timeout=5000); page.wait_for_timeout(300)
        page.click('#homeBack', timeout=5000); page.wait_for_timeout(200)
        if page.is_visible('#resume'): page.click('#resume', timeout=5000); page.wait_for_timeout(300)
        page.click('nav [data-go="profile"]'); page.click('#profNear', timeout=5000); page.wait_for_timeout(200)
        page.click('#nearClose', timeout=5000)
        page.click('#dtBtn', timeout=5000); page.wait_for_timeout(900)
        page.click('#dtClose', timeout=5000)
        page.click('nav [data-go="recipes"]'); page.click('#recCatalog [data-rec] >> nth=0', timeout=5000); page.wait_for_timeout(400)
    except Exception as e:
        errs.append('blocage : ' + str(e).split('\n')[0][:120])
    if errs:
        errs_out.append(f'{key} = {raw[:70]} → ' + ' | '.join(dict.fromkeys(errs))[:300])
    ctx.close()


def monkey(b, base, steps, seed, errs_out, offline=False):
    rnd = random.Random(seed)
    ctx = b.new_context(viewport={'width': 390, 'height': 844}, locale='fr-FR', geolocation={'latitude': RENNES[0], 'longitude': RENNES[1]}, permissions=['geolocation'])
    setup_routes(ctx, {})
    shop = [{'code': '3017620422003', 'p': {'code': '3017620422003', 'product_name': 'Glace vanille', 'brands': "Carte d'Or", 'stores_tags': ['carrefour']}, 'done': False, 'at': 1}]
    ctx.add_init_script("""(() => { try { if (sessionStorage.getItem('__init')) return; sessionStorage.setItem('__init', '1');
      localStorage.setItem('rs2:profile', %s); localStorage.setItem('rs2:geoAsked', '1'); localStorage.setItem('rs2:shop', %s); } catch (e) {} })();""" % (json.dumps(json.dumps(PROFILE)), json.dumps(json.dumps(shop))))
    page = ctx.new_page()
    ctx.on('page', lambda p: p.close())                      # liens externes ouverts dans un nouvel onglet
    errs = []
    page.on('pageerror', lambda e: errs.append(str(e).split('\n')[0]))
    page.on('dialog', lambda d: d.accept() if rnd.random() < 0.5 else d.dismiss())
    page.goto(base)
    page.wait_for_timeout(1500)
    if offline:
        ctx.set_offline(True)
    texts = ['', 'glace', 'xx', '3017620422003', '35000', 'rennes', '12 rue de lorient', 'à<b>"\'', '0000']
    for i in range(steps):
        try:
            els = page.query_selector_all('button:not([disabled]), [role="tab"], input[type=checkbox], select, input[type=text], input[type=search], input[inputmode]')
            vis = [e for e in els if e.is_visible()]
            if not vis:
                page.keyboard.press('Escape'); continue
            el = rnd.choice(vis)
            tag = el.evaluate('e => e.tagName.toLowerCase() + (e.type ? ":" + e.type : "")')
            if tag.startswith('select'):
                opts = el.evaluate('e => [...e.options].map(o => o.value)')
                el.select_option(rnd.choice(opts))
            elif tag in ('input:text', 'input:search', 'input:tel', 'input:number'):
                el.fill(rnd.choice(texts)); el.press('Enter')
            else:
                el.click(timeout=1500)
            page.wait_for_timeout(rnd.choice([30, 80, 200]))
            if rnd.random() < 0.05:
                page.keyboard.press('Escape')
        except Exception:
            pass
    page.wait_for_timeout(1500)
    if errs:
        errs_out.append(('hors ligne ' if offline else '') + f'parcours au hasard {seed} → ' + ' | '.join(dict.fromkeys(errs))[:400])
    ctx.close()


def main():
    steps = int(sys.argv[1]) if len(sys.argv) > 1 else 150
    only = sys.argv[2] if len(sys.argv) > 2 else ''        # « donnees » ou « clics » pour ne lancer qu'une partie
    httpd, base = serve()
    with sync_playwright() as p:
        b = p.chromium.launch()
        if only != 'clics':
            print('1. Données enregistrées abîmées', flush=True)
            errs, n = [], 0
            for key in SPECIFIC:
                for raw in JUNK + [json.dumps(v) for v in SPECIFIC[key]]:
                    run_case(b, base, key, raw, errs); n += 1
            check(not errs, f'{n} cas de données abîmées sans erreur' + ('' if not errs else ' :\n    ' + '\n    '.join(errs)))
        if only != 'donnees':
            print('2. Clics au hasard', flush=True)
            errs = []
            for seed in (1, 2, 3):
                monkey(b, base, steps, seed, errs)
            monkey(b, base, steps, 4, errs, offline=True)
            check(not errs, f'{4 * steps} clics au hasard (dont hors ligne) sans erreur' + ('' if not errs else ' :\n    ' + '\n    '.join(errs)))
        b.close()
    httpd.shutdown()
    print('\n' + ('TOUT EST OK' if not FAIL else f'{len(FAIL)} ÉCHEC(S)'))
    sys.exit(1 if FAIL else 0)


if __name__ == '__main__':
    main()
