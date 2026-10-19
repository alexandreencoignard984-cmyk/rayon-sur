"""Non-régression des bugs corrigés : un test par bug, pour qu'ils ne reviennent pas."""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from localisation import serve, new_page, setup_routes, check, FAIL, RENNES, wait_near, OUT
from playwright.sync_api import sync_playwright

httpd, base = serve()
with sync_playwright() as p:
    b = p.chromium.launch(args=['--use-fake-ui-for-media-stream', '--use-fake-device-for-media-stream'])

    print('1. « Effacer toutes mes données » efface aussi l\'adresse, la position et le test des liens')
    home = {'main': '12 Rue de Lorient', 'city': 'Rennes', 'full': '12 Rue de Lorient 35000 Rennes', 'kind': 'housenumber', 'lat': 48.1005, 'lon': -1.7005}
    ctx = b.new_context(viewport={'width': 390, 'height': 844}, locale='fr-FR', geolocation={'latitude': RENNES[0], 'longitude': RENNES[1]}, permissions=['geolocation'])
    setup_routes(ctx, {})
    # garde par cookie : l'effacement vide aussi sessionStorage
    ctx.add_init_script("""(() => { if (document.cookie.includes('init=1')) return; document.cookie = 'init=1; path=/';
      localStorage.setItem('rs2:profile', JSON.stringify({ sel:['milk'], traces:false, words:[] })); localStorage.setItem('rs2:geoAsked', '1');
      localStorage.setItem('rs2:loc', %s); })();""" % json.dumps(json.dumps({'mode': 'city', 'home': home})))
    page = ctx.new_page(); errs = []
    page.on('pageerror', lambda e: errs.append(str(e)))
    page.goto(base)
    wait_near(page)
    page.evaluate("() => localStorage.setItem('rs2:drivetest', '{}')")
    page.on('dialog', lambda d: d.accept())
    page.click('nav [data-go="profile"]'); page.click('#resetAll')
    page.wait_for_load_state('load'); page.wait_for_timeout(800)
    left = page.evaluate("() => Object.keys(localStorage).filter(k => k.startsWith('rs2:'))")
    check(not any(k in left for k in ['rs2:loc', 'rs2:near', 'rs2:drivetest', 'rs2:shop', 'rs2:profile']), 'plus rien d\'enregistré : ' + ','.join(left))
    check(page.is_visible('#onboard'), 'retour à l\'écran de bienvenue')
    ctx.close()

    print('2. Sauvegarde : recettes, adresse et réglages des magasins exportés puis réimportés')
    rec = [{'id': 'm1', 'n': 'Ma salade', 'i': [['thon'], ['tomate']]}]
    ctx = b.new_context(viewport={'width': 390, 'height': 844}, locale='fr-FR', accept_downloads=True)
    setup_routes(ctx, {})
    ctx.add_init_script("""(() => { if (sessionStorage.getItem('__init')) return; sessionStorage.setItem('__init', '1');
      localStorage.setItem('rs2:profile', JSON.stringify({ sel:['milk'], traces:false, words:[] })); localStorage.setItem('rs2:geoAsked', '1');
      localStorage.setItem('rs2:recipes', %s); localStorage.setItem('rs2:loc', %s);
      localStorage.setItem('rs2:flags', JSON.stringify({ '3017620422003': { al:['milk'], at:1, name:'Pâte à tartiner' } })); })();""" % (json.dumps(json.dumps(rec)), json.dumps(json.dumps({'mode': 'city', 'home': home, 'radius': 20, 'off': ['lidl']}))))
    page = ctx.new_page(); errs = []
    page.on('pageerror', lambda e: errs.append(str(e)))
    page.goto(base); page.wait_for_timeout(800)
    page.click('nav [data-go="list"]')
    page.click('summary:has-text("Sauvegarder")')
    with page.expect_download() as dl:
        page.click('#exportBtn')
    path = os.path.join(OUT, 'sauvegarde.json'); dl.value.save_as(path)
    data = json.load(open(path, encoding='utf-8'))
    check(data.get('flags', {}).get('3017620422003', {}).get('al') == ['milk'], 'produits signalés dans le fichier')
    check(data.get('recipes') == rec and data.get('stores', {}).get('home', {}).get('full') == home['full'] and data['stores']['radius'] == 20, 'recettes et adresse dans le fichier')
    page.evaluate("() => { localStorage.removeItem('rs2:recipes'); localStorage.removeItem('rs2:loc'); localStorage.removeItem('rs2:flags'); }")
    page.reload(); page.wait_for_timeout(600)
    page.on('dialog', lambda d: d.accept())
    page.click('nav [data-go="list"]'); page.click('summary:has-text("Sauvegarder")')
    page.set_input_files('#importFile', path); page.wait_for_timeout(800)
    got = page.evaluate("() => ({ rec:JSON.parse(localStorage.getItem('rs2:recipes') || '[]'), loc:JSON.parse(localStorage.getItem('rs2:loc') || '{}'), fl:JSON.parse(localStorage.getItem('rs2:flags') || '{}') })")
    check('3017620422003' in got['fl'], 'produits signalés réimportés')
    check(got['rec'] == rec and got['loc'].get('home', {}).get('full') == home['full'] and got['loc'].get('off') == ['lidl'], 'réimportés')
    page.click('nav [data-go="recipes"]')
    check('Ma salade' in page.inner_text('#recCatalog'), 'la recette réimportée apparaît')
    check(not errs, 'aucune erreur JavaScript' + (': ' + '; '.join(errs[:3]) if errs else ''))
    ctx.close()

    print('3. Caméra : deux appuis rapides n\'ouvrent qu\'un seul flux')
    ctx, page, errs, _ = new_page(b, base, granted=False)
    ctx.grant_permissions(['camera'])
    page.evaluate("""() => { window.__gum = 0; const g = navigator.mediaDevices.getUserMedia.bind(navigator.mediaDevices);
      navigator.mediaDevices.getUserMedia = c => { window.__gum++; return g(c); }; }""")
    page.click('nav [data-go="scan"]')
    page.evaluate("() => { document.querySelector('#startScan').click(); document.querySelector('#startScan').click(); }")
    page.wait_for_timeout(1500)
    check(page.evaluate('() => window.__gum') == 1, f"getUserMedia appelé {page.evaluate('() => window.__gum')} fois")
    page.click('nav [data-go="search"]'); page.wait_for_timeout(300)
    check(page.evaluate("() => !document.querySelector('#video').srcObject"), 'caméra coupée en quittant l\'écran')
    check(not errs, 'aucune erreur JavaScript' + (': ' + '; '.join(errs[:3]) if errs else ''))
    ctx.close()

    print('4. Photo illisible : message d\'erreur, pas de chargement sans fin')
    ctx, page, errs, _ = new_page(b, base, granted=False)
    page.click('nav [data-go="scan"]')
    bad = os.path.join(OUT, 'pas-une-image.jpg'); open(bad, 'wb').write(b'pas une image')
    page.set_input_files('#photo', bad)
    page.wait_for_function("() => !document.querySelector('#scanStatus .spin')", timeout=12000)
    check(page.evaluate("() => document.querySelector('#scanStatus').classList.contains('err')"), 'message : ' + page.inner_text('#scanStatus')[:70])
    check(not errs, 'aucune erreur JavaScript' + (': ' + '; '.join(errs[:3]) if errs else ''))
    ctx.close()

    print('5. Données abîmées : un produit mal formé dans la liste ne bloque pas l\'appli')
    shop = [{'code': 'a', 'p': {'code': 'a', 'product_name': 5, 'brands': ['x'], 'stores_tags': 'lidl'}}, None, {'code': 1}]
    ctx, page, errs, _ = new_page(b, base, granted=False, init={'rs2:shop': shop, 'rs2:profile': {'sel': 'milk', 'words': [1, 'palme']}, 'rs2:search': {'nutri': 'z', 'sort': 'zz', 'ran': True}})
    page.wait_for_timeout(1500)
    page.click('nav [data-go="list"]'); page.wait_for_timeout(300)
    check(page.locator('#shopList li.item').count() == 1, 'le produit lisible est gardé, les autres ignorés')
    check(page.evaluate("() => __RS.S.nutri === '' && __RS.S.sort === 'popularity'"), 'filtres invalides remis à zéro')
    check(page.evaluate("() => __RS.profile.words.join() === 'palme'"), 'profil réparé')
    check(not errs, 'aucune erreur JavaScript' + (': ' + '; '.join(errs[:3]) if errs else ''))
    ctx.close()
    b.close()
httpd.shutdown()
print('\n' + ('TOUT EST OK' if not FAIL else f'{len(FAIL)} ÉCHEC(S)'))
sys.exit(1 if FAIL else 0)
