"""Fiches produit : informations fiables. Allergènes repérés par Open Food Facts dans les ingrédients mais non
déclarés, listes d'ingrédients incomplètes ou mal lues, mise à jour en direct de la fiche, signalement personnel
d'un produit (« contient un de mes allergènes »).
Usage : python3 tests/fiches.py"""
import json, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from localisation import serve, new_page, check, FAIL, RENNES, wait_near
from playwright.sync_api import sync_playwright

BASE = 'sucre, eau, sel, riz'
httpd, base = serve()
with sync_playwright() as p:
    b = p.chromium.launch()
    ctx, page, errs, _ = new_page(b, base, geo=RENNES)
    page.wait_for_function('() => window.__RS && window.__RS.evaluate', timeout=30000)
    def ev(sel, extra=None):
        prod = {'code': '1', 'product_name': 'Produit test', 'brands': 'Marque', 'ingredients_text_fr': BASE, 'allergens_tags': [], 'traces_tags': [], 'categories_tags': []}
        prod.update(extra or {})
        return page.evaluate("""([sel, prod]) => { const R = window.__RS; R.profile.sel = new Set(sel); R.profile.words = []; R.profile.traces = false;
          const e = R.evaluate(prod); return [e.status, [...e.no, ...e.check].join(' | ')]; }""", [sel, prod])

    print('1. Ingrédients reconnus par Open Food Facts, allergène non déclaré')
    st, why = ev(['milk'], {'_ia': ['en:milk']})
    check(st == 'check' and 'Open Food Facts repère du lait' in why, f'lait repéré dans les ingrédients : à vérifier ({why})')
    st, why = ev(['lactose'], {'_ia': ['en:milk']})
    check(st == 'check', 'intolérance au lactose, lait repéré : à vérifier')
    check(ev(['lactose'], {'_ia': ['en:milk'], 'labels_tags': ['en:no-lactose']})[0] == 'ok', 'lait repéré mais étiqueté sans lactose : compatible (intolérance)')
    check(ev(['gluten'], {'_ia': ['en:gluten']})[0] == 'check', 'gluten repéré : à vérifier')
    check(ev(['gluten'], {'_ia': ['en:gluten'], 'allergens_tags': ['en:gluten']})[0] == 'no', 'gluten déclaré : exclu')
    check(ev(['gluten'], {'_ia': ['en:milk']})[0] == 'ok', 'allergène repéré qui n\'est pas dans le profil : sans effet')

    print('2. Fiabilité de la liste d\'ingrédients')
    st, why = ev(['milk'], {'_q': 'i'})
    check(st == 'check' and 'incomplète' in why, 'liste à compléter sur la fiche : à vérifier')
    st, why = ev(['milk'], {'_q': 'u'})
    check(st == 'check' and 'mal lus' in why, 'ingrédients mal lus par Open Food Facts : à vérifier')
    check(ev(['milk'], {'_q': 'u', 'allergens_tags': ['en:milk']})[0] == 'no', 'mal lus mais lait déclaré : exclu (pas adouci)')
    check(ev([], {'_q': 'iu'})[0] == 'ok', 'profil vide : pas de doute ajouté')
    lq = page.evaluate("""() => __RS.liveQuality({ states_tags:['en:ingredients-to-be-completed'], ingredients_tags:['fr:a','fr:b','en:wheat-flour','en:wheat','en:milk'], ingredients_n:3, unknown_ingredients_n:2, last_modified_t:1700000000 })""")
    check(lq['_q'] == 'iu' and lq['_ia'] == ['en:gluten', 'en:milk'] and lq['_mod'] == '2023-11-14', f'calcul en direct : {lq}')

    print('3. Signaler un produit : « contient un de mes allergènes »')
    page.evaluate("() => { const R = window.__RS; R.profile.sel = new Set(['milk', 'gluten']); }")
    page.reload(); page.wait_for_function('() => window.__RS && window.__RS.evaluate', timeout=30000)
    wait_near(page)
    page.click('#homeGrid [data-q="en:ice-creams-and-sorbets"]'); page.wait_for_selector('#list li.s-ok .name', timeout=20000)
    name = page.inner_text('#list li.s-ok .name >> nth=0')
    code = page.get_attribute('#list li.s-ok [data-open] >> nth=0', 'data-open')
    page.click('#list li.s-ok [data-open] >> nth=0'); page.wait_for_selector('#sheet[open] .flagbox')
    check('Compatible' in page.inner_text('#sheet .bigverdict'), 'produit compatible au départ : ' + name)
    page.click('#sheet .flagbox summary'); page.click('#sheet .flagbox [data-flag="milk"]'); page.wait_for_timeout(300)
    check('Exclu' in page.inner_text('#sheet .bigverdict') and 'Signalé par toi : contient lait' in page.inner_text('#sheet .reasons'), 'signalé « lait » : exclu, avec la raison')
    check('Exclu' in page.inner_text('#toast') or 'Signalé' in page.inner_text('#toast'), 'message de confirmation')
    check(page.get_attribute('#sheet .flagbox [data-flag="milk"]', 'aria-pressed') == 'true', 'puce « Lait » cochée')
    page.click('#sheetClose'); page.wait_for_timeout(300)
    check(page.locator(f'#list li.s-ok [data-open="{code}"]').count() == 0, 'il disparaît des compatibles')
    page.reload(); page.wait_for_function('() => window.__RS && window.__RS.evaluate', timeout=30000)
    check(page.evaluate(f"() => !!__RS.getFlags()['{code}']"), 'signalement gardé après rechargement')
    page.click('#homeGrid [data-q="en:ice-creams-and-sorbets"]'); page.wait_for_selector('#list li .name', timeout=20000)
    page.click('.tab[data-s="no"]'); page.wait_for_timeout(1500)
    check(page.locator(f'#list [data-open="{code}"]').count() == 1, 'il apparaît dans « Exclus »')
    page.click(f'#list [data-open="{code}"]'); page.wait_for_selector('#sheet[open] .flagbox[open]')
    page.click('#sheet .flagbox [data-flag="milk"]'); page.wait_for_timeout(300)
    check('Compatible' in page.inner_text('#sheet .bigverdict') and not page.evaluate(f"() => !!__RS.getFlags()['{code}']"), 'signalement retiré : compatible à nouveau')
    page.click('#sheetClose'); page.wait_for_timeout(200)

    print('4. Fiche mise à jour en direct depuis Open Food Facts')
    page.click('.tab[data-s="ok"]'); page.wait_for_timeout(500)
    code2 = page.get_attribute('#list li.s-ok [data-open] >> nth=1', 'data-open')
    live = {'status': 1, 'product': {'code': code2, 'product_name': 'Produit mis à jour', 'allergens_tags': ['en:milk'], 'traces_tags': [],
            'ingredients_text_fr': 'sucre, lait écrémé en poudre, eau', 'states_tags': ['en:ingredients-completed'], 'ingredients_tags': ['en:sugar', 'en:skimmed-milk-powder', 'en:milk', 'en:dairy', 'en:water'],
            'ingredients_n': 3, 'unknown_ingredients_n': 0, 'last_modified_t': 1760000000}}
    ctx.route(re.compile(r'.*openfoodfacts\.org/api/v2/product/' + code2 + r'.*'), lambda r: r.fulfill(status=200, body=json.dumps(live), headers={'content-type': 'application/json', 'access-control-allow-origin': '*'}))
    page.click(f'#list li.s-ok [data-open="{code2}"]'); page.wait_for_selector('#sheet[open]')
    page.wait_for_function("() => /Exclu/.test(document.querySelector('#sheet .bigverdict').textContent)", timeout=8000)
    check('Contient : lait' in page.inner_text('#sheet .reasons'), 'verdict recalculé avec la fiche à jour : exclu')
    check('vérifiée en direct' in page.inner_text('#sheet .links') and 'fiche modifiée le' in page.inner_text('#sheet .links'), 'source : ' + page.inner_text('#sheet .links .src'))
    check('mise à jour en direct' in page.inner_text('#toast'), 'message « Fiche mise à jour en direct »')
    page.click('#sheetClose'); page.wait_for_timeout(300)
    check(page.locator(f'#list li.s-ok [data-open="{code2}"]').count() == 0, 'la liste de résultats suit la fiche à jour')
    txt = page.evaluate("() => document.body.innerText")
    page.click('#list li [data-open] >> nth=0'); page.wait_for_selector('#sheet[open]')
    check('ne garantit pas' in page.inner_text('#sheet') or page.locator('#sheet .tags .tag').count() > 0, 'allergènes non déclarés : rappel que l\'étiquette fait foi')
    check(not errs, 'aucune erreur JavaScript' + (': ' + '; '.join(errs[:3]) if errs else ''))
    b.close()
httpd.shutdown()
print('\n' + ('TOUT EST OK' if not FAIL else f'{len(FAIL)} ÉCHEC(S)'))
sys.exit(1 if FAIL else 0)
