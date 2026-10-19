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
    check(all(re.match(r'https://(www\.carrefour\.fr/s\?q=|www\.biocoop\.fr/catalogsearch/result/\?q=|www\.leclercdrive\.fr/$|www\.coursesu\.com/recherche\?q=)', h) for h in hrefs), f'{len(hrefs)} liens vers la recherche des sites')
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
    ctx.close()

    print('Carte « Stock au drive » : bonne enseigne d\'abord, mauvais lien signalé')
    A = {'code': '3017620422003', 'product_name': 'Pâte à tartiner', 'brands': 'Nutella', 'quantity': '400 g', 'stores_tags': ['carrefour']}
    C = {'code': '123456', 'product_name': 'Biscuits fourrés', 'brands': 'Marque Test', 'stores_tags': []}
    D = {'code': '777888', 'product_name': 'Lait demi-écrémé', 'brands': 'U', 'stores_tags': ['magasins-u']}
    shop = [{'code': x['code'], 'p': x, 'done': False, 'at': i + 1} for i, x in enumerate([D, C, A])]
    ctx, page, errs, _ = new_page(b, base, geo=RENNES, init={'rs2:shop': shop})
    wait_near(page)
    page.add_init_script("window.open = u => { (window.__opened = window.__opened || []).push(u); return null; };")
    page.evaluate("() => { window.open = u => { (window.__opened = window.__opened || []).push(u); return null; }; }")
    def open_a():
        page.click('nav [data-go="list"]')
        page.click('#shopList [data-open="3017620422003"]'); page.wait_for_selector('#sheet[open] .drivebtn')
    open_a()
    ids = page.evaluate("p => __RS.linkChains(p)", A)
    top = page.eval_on_selector_all('#sheetBody .card:has(.drives) > .drives > .drivebtn b', 'els => els.map(e => e.textContent)')
    more = page.eval_on_selector_all('#sheetBody .dmore .drivebtn b', 'els => els.map(e => e.textContent)')
    check(ids[0] == 'carrefour' and len(ids) >= 2, 'enseignes proposées : ' + ','.join(ids))
    check(top == ['Carrefour'], 'en premier, seulement l\'enseigne où le produit a été vu : ' + ','.join(top))
    check(len(more) == len(ids) - 1 and not page.evaluate("document.querySelector('#sheetBody .dmore').open"), 'les autres enseignes repliées dans « Chercher aussi chez … »')
    check('Chercher aussi chez' in page.inner_text('#sheetBody .dmore summary') and page.locator('#sheetBody .dwarn').count() == 0, 'titre clair, pas d\'avertissement')
    first = page.locator('#sheetBody .drivebtn').first
    href0 = first.locator('.dmain').get_attribute('href')
    check(href0 == 'https://www.carrefour.fr/s?q=3017620422003', 'Carrefour : produit exact par le code-barres')
    check(first.locator('.dfix').inner_text() == 'Mauvais produit ?', 'bouton « Mauvais produit ? » sous chaque lien')
    first.locator('.dfix').click(); page.wait_for_selector('#toast.show')
    first = page.locator('#sheetBody .drivebtn').first
    href1 = first.locator('.dmain').get_attribute('href')
    check(href1.startswith('https://www.carrefour.fr/s?q=Nutella'), 'après signalement : recherche par le nom (' + href1[-40:] + ')')
    check(page.evaluate("() => window.__opened || []") == [href1], 'la nouvelle recherche s\'ouvre tout de suite')
    check('par le nom' in page.inner_text('#toast') and first.locator('.dfix').inner_text() == 'Revenir au premier lien', 'message clair et bouton pour revenir')
    check(page.evaluate("() => JSON.parse(localStorage.getItem('rs2:drivefix'))") == {'3017620422003|carrefour': 'nom'}, 'signalement enregistré pour ce produit et cette enseigne')
    page.reload(); wait_near(page); open_a()
    check(page.locator('#sheetBody .drivebtn .dmain').first.get_attribute('href') == href1, 'signalement gardé après rechargement')
    other = page.eval_on_selector_all('#sheetBody .dmore .dmain', 'els => els.map(e => e.getAttribute("href"))')
    check(len(other) == len(ids) - 1 and not any('carrefour' in h for h in other) and ('https://www.leclercdrive.fr/' in other or 'leclerc' not in ids),
          'les autres enseignes gardent leur propre lien')
    page.locator('#sheetBody .drivebtn .dfix').first.click(); page.wait_for_timeout(200)
    check(page.locator('#sheetBody .drivebtn .dmain').first.get_attribute('href') == href0 and page.evaluate("() => JSON.parse(localStorage.getItem('rs2:drivefix'))") == {}, '« Revenir au premier lien » remet le code-barres')
    page.evaluate("() => history.back()"); page.wait_for_timeout(300)

    page.click('#shopList [data-open="123456"]'); page.wait_for_selector('#sheet[open] .drivebtn')
    check(page.locator('#sheetBody .dwarn').count() == 1 and page.locator('#sheetBody .dmore').count() == 0, 'produit vu nulle part : avertissement « peut-être pas vendu »')
    btn = page.locator('#sheetBody .drivebtn').first
    h = btn.locator('.dmain').get_attribute('href'); name = btn.locator('b').inner_text()
    btn.locator('.dfix').click(); page.wait_for_timeout(200)
    h2 = page.locator('#sheetBody .drivebtn .dmain').first.get_attribute('href')
    check('Biscuits' in h.replace('%20', ' ') and h2.endswith('Marque%20Test') and 'Biscuits' not in h2, f'{name} : recherche par nom, puis toute la marque après signalement')
    check(page.locator('#sheetBody .drivebtn .dalt').first.inner_text().startswith('Chercher « Marque Test'), 'lien de secours : revenir à la recherche par nom')
    page.evaluate("() => history.back()"); page.wait_for_timeout(300)

    page.click('#whereList [data-drive="carrefour"]'); page.wait_for_selector('#driveSheet[open] #driveList li')
    names = page.eval_on_selector_all('#driveList li b', 'els => els.map(e => e.textContent)')
    check(names == ['Pâte à tartiner', 'Biscuits fourrés', 'Lait demi-écrémé'], 'Ma liste chez Carrefour : produits vus chez Carrefour d\'abord, marque U à la fin (' + ' / '.join(names) + ')')
    meta = page.inner_text('#driveList')
    check('code-barres' in meta and 'toute la marque Marque Test' in meta, 'chaque produit dit comment il est cherché (code-barres, nom, marque)')
    check(not errs, 'aucune erreur JavaScript' + (': ' + '; '.join(errs[:3]) if errs else ''))
    ctx.close()

    print('Liens corrigés d\'après la sonde des vrais sites (19/10/2026)')
    R = {'code': '3564700007433', 'product_name': 'Fromage blanc au lait demi-écrémé', 'brands': 'Délisse, Marque Repère', 'stores_tags': ['e-leclerc']}
    LI = {'code': '4056489123456', 'product_name': 'Pesto rosso', 'brands': 'Baresa', 'stores_tags': ['lidl']}
    shop = [{'code': R['code'], 'p': R, 'done': False, 'at': 1}, {'code': LI['code'], 'p': LI, 'done': False, 'at': 2}]
    ctx, page, errs, _ = new_page(b, base, geo=RENNES, init={'rs2:shop': shop, 'rs2:drivefix': {'3564700007433|leclerc': 'nom'}})
    ctx.grant_permissions(['clipboard-read', 'clipboard-write'], origin=base.rstrip('/'))
    ctx.route(re.compile(r'.*leclercdrive.*'), lambda r: r.fulfill(status=200, content_type='text/html', body='<title>Leclerc Drive</title>'))
    wait_near(page)
    E = lambda expr, arg=None: page.evaluate(expr, arg)
    prince = {'code': '7622210449283', 'product_name': 'Prince Goût Chocolat au blé complet', 'brands': 'Mondelez'}
    check(E("p => __RS.driveUrl(p, 'auchan')", prince) == 'https://www.auchan.fr/recherche?text=7622210449283', 'Auchan : recherche par code-barres (produit exact sur le site)')
    check(E("p => __RS.driveUrl(p, 'leclerc')", prince) == 'https://www.leclercdrive.fr/', 'Leclerc : le site du drive, plus la recherche de e.leclerc (livres, jouets)')
    terms = {
        ('Mondelez', 'Prince Goût Chocolat au blé complet'): 'Prince Chocolat blé',
        ('Lindt & Sprüngli', 'Extra fine dark chocolate'): 'Lindt Extra fine',
        ('Mondelez, LU, Prince', 'Prince chocolat'): 'LU Prince chocolat',
        ('Ferrero, Nutella', 'Nutella'): 'Nutella',
        ('Coca-Cola', 'Coca-Cola'): 'Coca-Cola',
        ('Danone, Activia', 'Activia nature'): 'Activia nature',
        ('Nestlé', 'Dessert chocolat noir'): 'Nestlé Dessert chocolat',
    }
    bad = []
    for (br, nm), want in terms.items():
        got = E("p => __RS.driveTerms(p, 'u')", {'code': '1', 'product_name': nm, 'brands': br})
        if got != want: bad.append(f'{br} / {nm} : « {got} » au lieu de « {want} »')
    check(not bad, 'recherche par nom : la marque du paquet, pas le fabricant (Mondelez, Lindt & Sprüngli…)' + ('' if not bad else ' :\n    ' + '\n    '.join(bad)))
    pic = {'code': '3270160680276', 'product_name': 'Velouté courge butternut carotte navet', 'brands': 'Le Bio par Picard'}
    check(E("p => __RS.driveTerms(p, 'picard')", pic) == 'Velouté courge butternut', 'Picard : recherche sans la marque (« Le Bio par Picard » ouvrait le rayon bio)')
    check(E("p => __RS.driveMode(p, 'leclerc')", R) == 'site', 'ancien signalement sur Leclerc sans effet : toujours le site du drive')

    page.click('nav [data-go="list"]')
    page.click('#shopList [data-open="3564700007433"]'); page.wait_for_selector('#sheet[open] .drivebtn')
    row = page.locator('#sheetBody .drivebtn').first
    t = row.inner_text()
    check(page.locator('#sheetBody .drivebtn').count() == 1 and 'E.Leclerc' in t and 'Ouvrir le drive' in t, 'Marque Repère : seulement Leclerc, bouton « Ouvrir le drive »')
    cp = row.locator('.dmain').get_attribute('data-cp')
    check(cp == 'Délisse Fromage blanc' and f'« {cp} » est copié' in t, 'le nom à coller est annoncé : ' + str(cp))
    check(row.locator('.dfix').count() == 0, 'pas de « Mauvais produit ? » quand il n\'y a pas d\'autre recherche')
    with ctx.expect_page() as pop:
        row.locator('.dmain').click()
    pop.value.close()
    page.wait_for_selector('#toast.show')
    check(E("() => navigator.clipboard.readText()") == cp and 'copié' in page.inner_text('#toast'), 'en touchant : nom copié dans le presse-papiers, message affiché')
    page.evaluate("() => history.back()"); page.wait_for_timeout(300)
    page.click('#shopList [data-open="4056489123456"]'); page.wait_for_selector('#sheet[open] .drivebtn')
    t = page.inner_text('#sheetBody .card:has(.drives)')
    check(page.locator('#sheetBody .drivebtn.dstore').count() == 1 and page.locator('#sheetBody .drivebtn a.dmain').count() == 0 and 'à prendre en magasin' in t,
          'Lidl : pas de lien vers son site (promos et non alimentaire), « à prendre en magasin »')
    check(page.locator('#sheetBody .dhelp:not(.dmore)').count() == 0 or page.locator('#sheetBody .dhelp [data-copy]').count() == 0, 'pas de lien à copier pour Lidl')
    page.evaluate("() => history.back()"); page.wait_for_timeout(300)
    check(page.locator('#whereList [data-drive="lidl"]').count() == 0, 'Ma liste : pas de bouton « drive » pour Lidl')
    if page.locator('#whereList [data-drive="leclerc"]').count():
        page.click('#whereList [data-drive="leclerc"]'); page.wait_for_selector('#driveSheet[open] #driveList li')
        check(page.locator('#driveList a[data-cp]').count() >= 1 and page.locator('#driveList a[data-cp]').count() == page.locator('#driveList a.dmain').count() and 'est copié' in page.inner_text('#driveList'),
              'Ma liste chez Leclerc : chaque produit copie son nom')
        page.evaluate("() => history.back()"); page.wait_for_timeout(300)

    print('Mon drive Leclerc : recherche directe dans le magasin choisi')
    P = lambda u: E("u => __RS.parseLeclerc(u)", u)
    check(P('https://fd6-courses.leclercdrive.fr/magasin-113521-113521-rennes---cleunay.aspx') == {'id': '113521', 'id2': '113521', 'name': 'Rennes – Cleunay'}, 'adresse du site de bureau reconnue (n° et nom du magasin)')
    check(P('https://m-courses.leclercdrive.fr/magasin-053701-053701/recherche/lait') == {'id': '053701', 'id2': '053701', 'name': ''}, 'adresse du site mobile reconnue')
    check(P('Regarde https://m-courses.leclercdrive.fr/magasin-171201-Trappes/accueil') == {'id': '171201', 'id2': '171201', 'name': 'Trappes'}, 'adresse collée au milieu d\'un texte')
    check(P('https://www.leclercdrive.fr/') is None and P('https://www.e.leclerc/mag/e-leclerc-cleunay') is None, 'adresse sans magasin refusée')
    page.click('#shopList [data-open="3564700007433"]'); page.wait_for_selector('#sheet[open] .drivebtn')
    page.click('#sheetBody [data-lec]'); page.wait_for_selector('#lecSheet[open]')
    page.fill('#lecUrl', 'https://www.e.leclerc/mag/e-leclerc-cleunay'); page.click('#lecForm [type="submit"]')
    check('leclercdrive.fr/magasin-' in page.inner_text('#lecMsg') and page.evaluate("() => document.querySelector('#lecSheet').open"), 'mauvaise adresse : message clair, la fiche reste ouverte')
    page.fill('#lecUrl', 'https://fd6-courses.leclercdrive.fr/magasin-113521-113521-rennes---cleunay.aspx'); page.click('#lecForm [type="submit"]')
    page.wait_for_selector('#toast.show'); page.wait_for_timeout(300)
    row = page.locator('#sheetBody .drivebtn').first
    href = row.locator('.dmain').get_attribute('href')
    check(href == 'https://m-courses.leclercdrive.fr/magasin-113521-113521/recherche/D%C3%A9lisse%20Fromage%20blanc', 'lien Leclerc : recherche du produit dans ton drive (' + href[-60:] + ')')
    t = row.inner_text()
    check('Ton drive : Rennes – Cleunay' in t and 'Chercher' in t and row.locator('.dmain').get_attribute('data-cp') is None and row.locator('[data-lec]').count() == 0, 'la ligne affiche ton drive, plus de copie du nom')
    check(row.locator('.dfix').count() == 1, '« Mauvais produit ? » disponible (recherche par la marque)')
    check(E("() => JSON.parse(localStorage.getItem('rs2:leclerc'))") == {'id': '113521', 'id2': '113521', 'name': 'Rennes – Cleunay'}, 'drive enregistré')
    page.evaluate("() => history.back()"); page.wait_for_timeout(300)
    page.reload(); wait_near(page)
    page.click('nav [data-go="profile"]')
    check('Rennes – Cleunay' in page.inner_text('#lecBtn'), 'Profil : « Mon drive Leclerc » affiche ton magasin')
    page.click('#lecBtn'); page.wait_for_selector('#lecSheet[open]')
    page.click('#lecForget'); page.wait_for_timeout(200)
    check(E("() => localStorage.getItem('rs2:leclerc')") in (None, 'null') and 'Pas encore choisi' in page.inner_text('#lecBtn'), '« Oublier ce drive » : retour à l\'accueil du drive')
    page.click('#lecClose'); page.wait_for_timeout(200)
    check(not errs, 'aucune erreur JavaScript' + (': ' + '; '.join(errs[:3]) if errs else ''))
    b.close()
httpd.shutdown()
print('\n' + ('TOUT EST OK' if not FAIL else f'{len(FAIL)} ÉCHEC(S)'))
sys.exit(1 if FAIL else 0)
