"""Verdicts allergènes : un ingrédient à risque doit donner « À vérifier » (ou « Exclu »), jamais « Compatible »,
même quand la fiche Open Food Facts ne déclare pas l'allergène. Et les faux amis (lait de coco, noix de coco,
chapelure sans gluten…) ne doivent pas exclure un produit compatible.
Usage : python3 tests/verdicts.py"""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from localisation import serve, new_page, check, FAIL
from playwright.sync_api import sync_playwright

BASE = 'sucre, eau, sel, '
# (allergène du profil, ingrédients, verdict attendu)
CASES = [
    # gluten : produits à base de blé où le mot « blé » n'apparaît pas
    ('gluten', 'chapelure', 'check'), ('gluten', 'semoule', 'check'), ('gluten', 'couscous', 'check'), ('gluten', 'boulgour', 'check'),
    ('gluten', 'seitan', 'check'), ('gluten', 'pain grillé', 'check'), ('gluten', 'panure', 'check'), ('gluten', 'petit épeautre', 'check'),
    ('gluten', 'chapelure sans gluten', 'ok'), ('gluten', 'semoule de maïs', 'ok'), ('gluten', 'farine de riz', 'ok'), ('gluten', 'pain sans gluten', 'ok'),
    # lait
    ('milk', 'lactalbumine', 'check'), ('milk', 'kéfir', 'check'), ('milk', 'skyr', 'check'), ('milk', 'lacto-sérum', 'check'), ('milk', 'paneer', 'check'),
    ('milk', 'kéfir de fruits', 'ok'), ('milk', 'beurre de cacao', 'ok'), ('milk', 'lait de coco', 'ok'), ('milk', 'crème de marrons', 'ok'),
    # œufs
    ('eggs', 'ovoproduits', 'check'), ('eggs', 'mayonnaise', 'check'), ('eggs', 'meringue', 'check'), ('eggs', 'albumine', 'check'), ('eggs', 'albumine de lait', 'ok'),
    # fruits à coque
    ('nuts', 'gianduja', 'check'), ('nuts', 'nougat', 'check'), ('nuts', 'pralin', 'check'), ('nuts', 'pâte de noisette', 'check'),
    ('nuts', 'noix de coco', 'ok'), ('nuts', 'noix de Saint-Jacques', 'ok'), ('nuts', 'noix de St Jacques', 'ok'),
    # soja, sésame
    ('soybeans', 'miso', 'check'), ('soybeans', 'tamari', 'check'), ('soybeans', 'tempeh', 'check'),
    ('sesame', 'gomasio', 'check'), ('sesame', 'halva', 'check'),
    # poissons, crustacés, mollusques
    ('fish', 'nuoc-mâm', 'check'), ('fish', 'sauce Worcestershire', 'check'), ('fish', 'églefin', 'check'), ('fish', 'lieu noir', 'check'), ('fish', 'tarama', 'check'),
    ('crustaceans', 'gambas', 'check'), ('crustaceans', 'krill', 'check'),
    ('molluscs', 'noix de Saint-Jacques', 'check'), ('molluscs', 'bulots', 'check'), ('molluscs', 'calamars', 'check'), ('molluscs', 'palourdes', 'check'),
    ('molluscs', 'fruits à coque', 'ok'),
    ('fish', 'caviar', 'check'), ('fish', "caviar d'aubergines", 'ok'), ('fish', 'caviar de tomates', 'ok'), ('fish', 'N. di lotte : vedere collo', 'ok'), ('fish', 'lotte', 'check'),
    ('gluten', "semoule d'ail", 'ok'), ('gluten', 'épices pour couscous', 'ok'),
    # sulfites
    ('sulphites', 'conservateur : E-220', 'check'), ('sulphites', 'E 224', 'check'), ('sulphites', 'E223', 'check'),
    # 3.14 : sulfites écrits « disulfite », fromages nommés sans le mot « lait », biscuits, morue, cacahouète
    ('sulphites', 'conservateur : disulfite de potassium', 'check'), ('sulphites', 'sodium metabisulphite', 'check'), ('sulphites', 'disulfites de sodium', 'check'),
    ('milk', 'emmental 9,5 %', 'check'), ('milk', 'parmigiano reggiano', 'check'), ('milk', 'grana padano AOP', 'check'), ('milk', 'feta', 'check'),
    ('milk', 'fromage de chèvre', 'check'), ('milk', 'chèvre 12 %', 'check'), ('milk', 'comté 13 %', 'check'), ('milk', 'cheddar', 'check'), ('milk', 'raclette', 'check'),
    ('milk', 'stracciatella', 'check'), ('milk', 'sauce béchamel', 'check'),
    ('milk', 'jambon de Franche-Comté', 'ok'), ('milk', 'beurre de cacahouète', 'ok'),
    ('gluten', 'biscuit 20 %', 'check'), ('gluten', 'brisures de cookies', 'check'), ('gluten', 'gaufrette', 'check'), ('gluten', 'madeleine 7,8 %', 'check'),
    ('gluten', 'speculoos', 'check'), ('gluten', 'croûtons', 'check'), ('gluten', 'génoise', 'check'), ('gluten', 'brioche', 'check'), ('gluten', 'wafer', 'check'),
    ('gluten', 'biscuits sans gluten', 'ok'),
    ('fish', 'foie de morue', 'check'), ('fish', 'filets de sébaste', 'check'), ('fish', 'capelan', 'check'),
    ('peanuts', 'cacahouètes grillées', 'check'), ('peanuts', 'beurre de cacahouète', 'check'),
    ('crustaceans', 'araignée de mer', 'check'),
]

httpd, base = serve()
with sync_playwright() as p:
    b = p.chromium.launch()
    ctx, page, errs, _ = new_page(b, base)
    page.wait_for_function('() => window.__RS && window.__RS.evaluate', timeout=30000)
    def verdict(sel, ingredients, extra=None, traces=False):
        prod = {'code': '1', 'product_name': 'Produit test', 'brands': 'Marque', 'ingredients_text_fr': ingredients, 'allergens_tags': [], 'traces_tags': [], 'categories_tags': []}
        prod.update(extra or {})
        return page.evaluate("""([sel, prod, traces]) => { const R = window.__RS;
          R.profile.sel = new Set(sel); R.profile.words = []; R.profile.traces = traces; return R.evaluate(prod).status; }""", [sel, prod, traces])

    print('1. Ingrédients à risque sans allergène déclaré')
    bad = []
    for sel, ing, want in CASES:
        got = verdict([sel], BASE + ing)
        if got != want: bad.append(f'{sel} / « {ing} » : {got} au lieu de {want}')
    check(not bad, f'{len(CASES)} cas de mots-clés' + ('' if not bad else ' :\n    ' + '\n    '.join(bad)))

    print('2. Règles de sécurité')
    check(verdict(['gluten'], BASE + 'farine de blé', {'allergens_tags': ['en:gluten']}) == 'no', 'allergène déclaré : exclu')
    check(verdict(['milk'], '') == 'check', 'ingrédients absents : à vérifier, jamais compatible')
    check(verdict(['milk'], 'Marque') == 'check', 'ingrédients illisibles (nom de marque recopié) : à vérifier')
    check(verdict(['milk'], BASE + 'cacao', {'traces_tags': ['en:milk']}) == 'check', 'traces de lait : à vérifier')
    check(verdict(['milk'], BASE + 'cacao', {'traces_tags': ['en:milk']}, traces=True) == 'no', 'traces de lait exclues sur demande : exclu')
    check(verdict(['milk'], BASE + 'cacao', {'categories_tags': ['en:cheeses']}) == 'no', 'fromage sans ingrédient laitier lisible : exclu (rayon laitier)')
    check(verdict(['gluten'], BASE + 'farine', {'categories_tags': ['en:breads']}) == 'check', 'pain sans mention du blé : à vérifier (rayon à gluten)')
    check(verdict(['lactose'], BASE + 'lait', {'labels_tags': ['en:no-lactose'], 'allergens_tags': ['en:milk']}) == 'ok', 'lait sans lactose étiqueté : compatible pour une intolérance')
    check(verdict(['milk'], BASE + 'lait', {'labels_tags': ['en:no-lactose'], 'allergens_tags': ['en:milk']}) == 'no', 'lait sans lactose : exclu pour une allergie au lait')
    check(verdict(['gluten', 'milk'], BASE + 'riz, huile de tournesol') == 'ok', 'produit sans risque : compatible')
    check(verdict(['gluten'], BASE + 'carottes', {'product_name': 'Légumes pour couscous'}) == 'ok', 'nom « Légumes pour couscous » : pas de faux doute sur le gluten')
    check(verdict(['gluten'], BASE + 'farine', {'product_name': 'Pain campagnard'}) == 'check', 'nom « Pain … » sans allergène déclaré : à vérifier')
    check(verdict(['fish'], BASE + 'farine', {'product_name': 'Filet de limande meunière'}) == 'check', 'nom « limande » : à vérifier')
    check(not errs, 'aucune erreur JavaScript' + (': ' + '; '.join(errs[:3]) if errs else ''))
    b.close()
httpd.shutdown()
print('\n' + ('TOUT EST OK' if not FAIL else f'{len(FAIL)} ÉCHEC(S)'))
sys.exit(1 if FAIL else 0)
