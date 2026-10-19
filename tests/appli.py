"""Non-régression sur la vraie base data/ : recherche, recettes, liste, profil, premier lancement."""
import json, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from localisation import serve, new_page, check, FAIL, RENNES, wait_near
from playwright.sync_api import sync_playwright

httpd, base = serve()
with sync_playwright() as p:
    b = p.chromium.launch()
    print('A. Recherche glaces chez Leclerc')
    ctx, page, errs, _ = new_page(b, base, geo=None, granted=False, init={'rs2:search': {'store': 'leclerc', 'rayon': 'en:ice-creams-and-sorbets', 'ran': True}})
    page.click('#homeGrid [data-q="en:ice-creams-and-sorbets"]')
    page.wait_for_selector('#results:not([hidden])', timeout=20000)
    n, prev = -1, -2
    for _ in range(40):                      # les verdicts arrivent par paquets : on attend que le compte ne bouge plus
        if n == prev and n > 0: break
        prev, n = n, int(page.inner_text('#n-ok') or 0); page.wait_for_timeout(500)
    check(n > 50, f'{n} glaces compatibles chez Leclerc')
    check(not page.is_visible('#nearLine'), 'pas de ligne « près de moi » pour un magasin choisi')
    print('B. Recette bolognaise')
    page.click('nav [data-go="recipes"]')
    page.click('text=Pâtes bolognaise')
    page.wait_for_selector('#recIngrText li', timeout=20000)
    page.wait_for_timeout(1500)
    check(page.locator('#recIngr li').count() >= 8, f"{page.locator('#recIngr li').count()} ingrédients")
    print('C. Liste et profil')
    page.click('nav [data-go="list"]'); page.wait_for_timeout(300)
    check(page.is_visible('#whereBox'), 'encadré « Où faire tes courses »')
    page.click('nav [data-go="profile"]'); page.wait_for_timeout(300)
    check('Position inconnue' in page.inner_text('#profNear'), 'Profil : position inconnue')
    want = re.search(r"const APP_VERSION = '([^']+)'", open(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'index.html'), encoding='utf-8').read()).group(1)
    check(page.inner_text('#appVersion') == want, 'version affichée ' + want)
    check(not errs, 'aucune erreur JavaScript' + (': ' + '; '.join(errs[:3]) if errs else ''))
    ctx.close()

    print('D. Premier lancement : accueil puis position')
    ctx = b.new_context(viewport={'width': 390, 'height': 844}, geolocation={'latitude': RENNES[0], 'longitude': RENNES[1]}, permissions=['geolocation'], locale='fr-FR')
    from localisation import setup_routes
    setup_routes(ctx, {})
    page = ctx.new_page(); errs = []
    page.on('pageerror', lambda e: errs.append(str(e)))
    page.goto(base)
    page.wait_for_selector('#onboard[open]')
    page.click('#obChips .chip >> nth=0')
    page.click('#obGo')
    wait_near(page)
    page.wait_for_timeout(500)
    check(page.evaluate('() => __RS.S.store') == 'near', 'après l\'accueil : magasins près de moi')
    check(page.is_visible('#nearLine'), 'ligne « près de moi » visible')
    check(not errs, 'aucune erreur JavaScript' + (': ' + '; '.join(errs[:3]) if errs else ''))
    ctx.close()
    b.close()
httpd.shutdown()
print('\n' + ('TOUT EST OK' if not FAIL else f'{len(FAIL)} ÉCHEC(S)'))
sys.exit(1 if FAIL else 0)
