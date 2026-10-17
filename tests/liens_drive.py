"""Page « Tester les liens drive » (Profil) : choix des produits sur la vraie base, notes, rapport."""
import os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from localisation import serve, new_page, check, FAIL, RENNES, wait_near
from playwright.sync_api import sync_playwright

httpd, base = serve()
with sync_playwright() as p:
    b = p.chromium.launch()
    print('Tester les liens drive')
    shop = [{'code': '1', 'p': {'code': '1', 'product_name': 'Râpé Gran Vegiano', 'brands': 'Nurishh'}, 'done': False, 'at': 1}]
    ctx, page, errs, _ = new_page(b, base, geo=RENNES, init={'rs2:shop': shop})
    ctx.grant_permissions(['clipboard-read', 'clipboard-write'])
    wait_near(page)
    page.click('nav [data-go="profile"]')
    page.click('#dtBtn')
    page.wait_for_function("() => document.querySelectorAll('#dtList li').length >= 15", timeout=30000)
    dt = page.evaluate('() => __RS.getDT()')
    check(dt['chains'] == ['carrefour', 'biocoop', 'leclerc', 'u'], 'enseignes testées : enseignes proches avec drive : ' + ','.join(dt['chains']))
    check(len(dt['items']) == 20, f"{len(dt['items'])} produits à tester")
    check(dt['items'][0]['p']['product_name'] == 'Râpé Gran Vegiano', 'les produits de ta liste en premier')
    cases = page.inner_text('#dtList')
    for k in ['nom bilingue', 'sans marque', 'marque distributeur', 'bio']:
        check(k in cases, f'cas difficile présent : {k}')
    terms = page.eval_on_selector_all('#dtList .meta', "els => els.map(e => (e.textContent.match(/« (.*?) »/) || [])[1]).filter(Boolean)")
    check(len(terms) == len(dt['items']) and all(0 < len(t) <= 60 for t in terms), 'une recherche courte pour chaque produit')
    hrefs = page.eval_on_selector_all('#dtList .dttop a:first-child', 'els => els.map(e => e.href)')
    check(all(re.match(r'https://(www\.carrefour\.fr/s\?q=|www\.biocoop\.fr/catalogsearch/result/\?q=|www\.e\.leclerc/recherche\?q=|www\.coursesu\.com/recherche\?q=)', h) for h in hrefs), f'{len(hrefs)} liens vers la recherche des sites')
    segs = page.locator('#dtList .seg')
    segs.nth(0).locator('[data-v="ko"]').click()
    segs.nth(1).locator('[data-v="ok"]').click()
    segs.nth(2).locator('[data-v="brand"]').click()
    segs.nth(2).locator('[data-v="brand"]').click()   # second appui : annule
    prog = page.inner_text('#dtProgress')
    check(prog.startswith('2 / ') and '1 trouvés' in prog and '1 rien' in prog, 'progression : ' + prog[:60])
    page.reload()
    page.click('nav [data-go="profile"]'); page.click('#dtBtn')
    page.wait_for_selector('#dtList li')
    check(page.inner_text('#dtProgress').startswith('2 / '), 'notes gardées après rechargement (retour depuis Safari)')
    page.click('#dtCopy'); page.wait_for_timeout(300)
    rep = page.evaluate('() => navigator.clipboard.readText()')
    check(rep.startswith('Rapport liens drive · Rayon sûr') and 'Rien trouvé :' in rep and '« Nurishh Râpé Gran »' in rep and 'Par enseigne :' in rep, 'rapport copié')
    print('   ' + rep.split('\n')[2])
    check(not errs, 'aucune erreur JavaScript' + (': ' + '; '.join(errs[:3]) if errs else ''))
    b.close()
httpd.shutdown()
print('\n' + ('TOUT EST OK' if not FAIL else f'{len(FAIL)} ÉCHEC(S)'))
sys.exit(1 if FAIL else 0)
