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
    # 3.23 : coques (coquillages) et autres mollusques, sans confondre avec les fruits à coque
    ('molluscs', 'coques', 'check'), ('molluscs', 'coques décortiquées 12 %', 'check'), ('molluscs', 'amandes de mer', 'check'),
    ('molluscs', 'berniques', 'check'), ('molluscs', 'clovisses', 'check'), ('molluscs', 'cockles', 'check'), ('molluscs', 'whelks', 'check'),
    ('molluscs', 'traces de fruits à coques', 'ok'), ('molluscs', 'noisettes en coque', 'ok'), ('molluscs', 'oeuf à la coque', 'ok'),
    ('molluscs', 'coques de cacao', 'ok'), ('molluscs', 'fruit à coque', 'ok'), ('molluscs', 'pâtes coquillettes', 'ok'),
    ('nuts', 'amandes de mer', 'ok'), ('nuts', 'amandes', 'check'),
    ('molluscs', 'fruits de mer, coques', 'check'), ('molluscs', 'fruits de mer (moules, coques, crevettes)', 'check'), ('molluscs', 'coques au naturel', 'check'),
    ('molluscs', 'chair de coques', 'check'), ('molluscs', 'fruits coque', 'ok'), ('molluscs', 'fruit(s) à coque', 'ok'), ('molluscs', 'fruits & coques', 'ok'),
    ('molluscs', 'fruitsà coque', 'ok'), ('molluscs', 'coque au chocolat noir 12 %', 'ok'), ('molluscs', 'coque de macaron', 'ok'),
    ('molluscs', 'céréales (billes et coques fourrées)', 'ok'), ('molluscs', 'contient : coque (noix)', 'ok'),
    # 3.24 : œufs mal lus sur l'emballage (« Œ » lu « CE »), ingrédients en langue étrangère ou en mots composés
    ('eggs', 'CEUFS de poules élevées en plein air 21 %', 'check'), ('eggs', 'ceuf dur 8 %', 'check'),
    ('gluten', 'harina de TRIGO', 'check'), ('gluten', 'farina di frumento', 'check'), ('gluten', 'farina di grano tenero tipo 00', 'check'),
    ('gluten', 'Weizenmehl', 'check'), ('gluten', 'Hartweizengrieß', 'check'), ('gluten', 'Gerstenmalzextrakt', 'check'), ('gluten', 'tarwebloem', 'check'),
    ('gluten', 'malto d\'orzo', 'check'), ('gluten', 'extracto de malta de cebada', 'check'), ('gluten', 'farinha de trigo', 'check'),
    ('gluten', 'Buchweizenmehl', 'ok'), ('gluten', 'harina de trigo sarraceno', 'ok'), ('gluten', 'Speisequarkzubereitung Magerstufe', 'ok'),
    ('milk', 'Magermilchpulver', 'check'), ('milk', 'Süßmolkenpulver', 'check'), ('milk', 'zoete weipoeder', 'check'), ('milk', 'volle melkpoeder', 'check'),
    ('milk', 'burro', 'check'), ('milk', 'lactosa', 'check'), ('milk', 'Butterreinfett', 'check'), ('milk', 'roomboter', 'check'),
    ('milk', 'Kokosmilch', 'ok'), ('milk', 'Milchsäure', 'ok'), ('milk', 'Kakaobutter', 'ok'), ('milk', 'cacaoboter', 'ok'), ('milk', 'nata de coco', 'ok'),
    ('milk', 'Kümmelkörner', 'ok'), ('milk', 'producto sin lactosa', 'ok'), ('milk', 'melkzuur', 'ok'), ('milk', 'leche de coco', 'check'),
    ('eggs', 'huevo', 'check'), ('eggs', 'uova fresche', 'check'), ('eggs', 'Vollei', 'check'), ('eggs', 'Hühnereiweißpulver', 'check'), ('eggs', 'eieren', 'check'),
    ('eggs', 'Eigelb', 'check'), ('eggs', 'tuorlo d\'uovo', 'check'), ('eggs', 'Sojaeiweiß', 'ok'),
    ('nuts', 'Haselnüsse', 'check'), ('nuts', 'Mandelscheiben', 'check'), ('nuts', 'nocciole', 'check'), ('nuts', 'avellanas', 'check'), ('nuts', 'hazelnoten', 'check'),
    ('nuts', 'avelines', 'check'), ('nuts', 'Kokosnuss', 'ok'), ('nuts', 'Muskatnuss', 'ok'), ('nuts', 'nuez moscada', 'ok'), ('nuts', 'extracto de nuez de cola', 'ok'),
    ('peanuts', 'Erdnüsse', 'check'), ('peanuts', 'pindakaas', 'check'), ('peanuts', 'arachidi', 'check'),
    ('soybeans', 'Sojalecithin', 'check'), ('soybeans', 'lecitina di soia', 'check'), ('sesame', 'Sesamsaat', 'check'), ('sesame', 'semillas de sésamo', 'check'),
    ('fish', 'Alaska-Seelachs', 'check'), ('fish', 'Thunfisch', 'check'), ('fish', 'tonno', 'check'), ('fish', 'pazifisches Meersalz', 'ok'), ('fish', 'Riboflavin, ryboflawina', 'ok'),
    ('crustaceans', 'Garnelen', 'check'), ('crustaceans', 'gamberetti', 'check'), ('molluscs', 'mejillones', 'check'), ('molluscs', 'Muschelnudeln', 'ok'),
    ('celery', 'Knollensellerie', 'check'), ('celery', 'sedano', 'check'), ('mustard', 'Senfsaat', 'check'), ('mustard', 'senape', 'check'),
    ('mustard', 'Hülsenfrüchte', 'ok'), ('mustard', 'Erbsenfaser', 'ok'), ('lupin', 'Lupinenmehl', 'check'), ('lupin', 'lupino', 'check'),
    # 3.25 : autres mots mal lus sur l'étiquette
    ('milk', 'lalt écrémé en poudre', 'check'), ('milk', 'poudre de iait', 'check'), ('milk', 'lactoserun en poudre', 'check'), ('milk', 'beure de cacao', 'ok'),
    ('eggs', "jaune doeuf", 'check'), ('eggs', "traces possibles d'eufs", 'check'), ('eggs', 'oeuts', 'check'), ('eggs', "blancs d'aeufs", 'check'),
    ('gluten', 'qluten', 'check'), ('gluten', 'giuten', 'check'), ('peanuts', 'traces darachides', 'check'), ('sesame', 'sesane', 'check'),
    ('mustard', 'graines de motarde', 'check'), ('nuts', 'nolsettes', 'check'), ('nuts', 'huile de nolx de coco', 'ok'),
    ('sulphites', 'enthalten Sulfit', 'check'), ('sulphites', 'anidride solforosa', 'check'), ('sulphites', 'metabisulfito sódico', 'check'),
    # 3.26 : allergènes discrets — sulfites mal écrits, collés ou étrangers
    ('sulphites', 'flour treatment agent (sodium disulphite)', 'check'), ('sulphites', 'antioxydant (disulphite de sodium)', 'check'),
    ('sulphites', 'antioxidant (sodium metbisulphite)', 'check'), ('sulphites', 'conservateur : metabisulfie de sodium', 'check'),
    ('sulphites', 'conservateur : disulfitede potassium', 'check'), ('sulphites', 'sucre etsulfites', 'check'), ('sulphites', 'Natriummetabisulfit', 'check'),
    ('sulphites', 'metabisulfita', 'check'), ('sulphites', 'konserveringsmiddel (kaliumdisulfitt)', 'check'), ('sulphites', 'sulfiti', 'check'),
    ('sulphites', 'metabisolfito di sodio', 'check'), ('sulphites', 'conservateur : anydride sulfureux', 'check'), ('sulphites', 'anhydridesulfureux', 'check'),
    ('sulphites', 'dioxyde de sulfure', 'check'), ('sulphites', "farce (pulpe d'ail, SO2, épaississant E401)", 'check'),
    ('sulphites', 'antioxydant : d_isulfite_ de potassium', 'check'), ('sulphites', 'sulfate de calcium, E330', 'ok'), ('sulphites', 'soja, so, eau', 'ok'),
    # chiffre de note collé au mot (« oeufs1 » = issu de l'agriculture biologique)
    ('eggs', 'oeufs1 (20%)', 'check'), ('eggs', "jaune d'ŒUF1", 'check'), ('eggs', 'OEUF9*', 'check'), ('fish', 'huile de POISSON1', 'check'),
    ('peanuts', 'Cacahuètes1, sel', 'check'), ('gluten', 'malt6dextrine', 'check'), ('sulphites', 'E224', 'check'),
    ('milk', 'vitamine b12, e471', 'ok'), ('milk', 'oméga3, colorant e160a', 'ok'),
    # moutarde
    ('mustard', 'mustardseed (yellow and brown)', 'check'), ('mustard', 'Contains sulphites, mustardseeds', 'check'), ('mustard', 'graines de moutardede Dijon', 'check'),
    ('mustard', 'MOSTERD', 'check'), ('mustard', 'mostaza', 'check'), ('mustard', 'mostarda', 'check'), ('mustard', 'sennepsfrø 26%', 'check'),
    ('mustard', 'SENNEPSPULVER', 'check'), ('mustard', 'krydderier (sennep, selleri)', 'check'), ('mustard', 'senap', 'check'), ('mustard', 'graines de sénevé', 'check'), ('mustard', 'Hülsenfrüchte, senf', 'check'),
    # céleri
    ('celery', 'krydderier (indeholder selleri)', 'check'), ('celery', 'arome (sadrže celer)', 'check'), ('celery', 'célerie, persil', 'check'),
    ('celery', 'arômes naturels (dontcéleri', 'check'), ('celery', 'knolselderij', 'check'), ('celery', 'celera', 'check'), ('celery', 'celeriae', 'check'),
    ('celery', 'persil, cerfeuil', 'ok'),
    # arachide
    ('peanuts', 'peanutbutter', 'check'), ('peanuts', 'huile darachide', 'check'), ('peanuts', 'huile dlarachide', 'check'), ('peanuts', 'arachideset sel', 'check'),
    ('peanuts', 'cacahuétes', 'check'), ('peanuts', 'acide arachidonique', 'ok'), ('peanuts', 'arachidonic acid', 'ok'),
    # poisson
    ('fish', 'raie', 'check'), ('fish', 'ailes de raies', 'check'), ('fish', 'filets d\'omble chevalier', 'check'), ('fish', 'Sole nettoyée', 'check'),
    ('fish', 'loup de mer', 'check'), ('fish', 'roussette', 'check'), ('fish', 'saumonette', 'check'), ('fish', 'tacaud', 'check'),
    ('fish', 'Oeufs de lompe saumurés', 'check'), ('fish', 'lump roe', 'check'), ('fish', 'fishes', 'check'), ('fish', "crème d'anchoïade", 'check'),
    ('fish', 'crème dlanchois', 'check'), ('fish', 'filets anchoislpois$onl', 'check'), ('fish', 'vin blanc (Roussette de Savoie)', 'ok'),
    ('fish', 'barres de céréales', 'ok'), ('fish', 'sucre de canne', 'ok'),
    ('fish', 'baguette cuite sur sole', 'ok'), ('fish', 'pomodori secchi al sole', 'ok'), ('fish', 'four à sole', 'ok'), ('fish', 'Peut contenir des traces de Sole', 'check'),
    # 3.27 : lacunes de mots-clés
    ('fish', 'sauce Worcester', 'check'), ('fish', 'rouille', 'check'), ('fish', 'garum', 'check'), ('fish', 'fumet', 'check'), ('fish', 'dashi', 'check'),
    ('milk', 'lactoferrine', 'check'), ('milk', 'lactoferrin', 'check'), ('eggs', 'Eiweiß', 'check'), ('eggs', 'Eiweiss', 'check'), ('peanuts', 'groundnut oil', 'check'),
    ('eggs', 'colorant : Ei29', 'ok'), ('milk', 'Traces de _lactose0_', 'check'),
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
    check(verdict(['molluscs'], 'oeufs frais', {'product_name': '6 œufs coque fermiers'}) == 'ok', 'œufs « coque » : pas de faux doute pour les mollusques')
    check(verdict(['molluscs'], 'coques 60 %, eau, sel', {'product_name': 'Coques au naturel'}) == 'check', 'boîte de coques : à vérifier pour les mollusques')
    # liste en espagnol lisible grâce aux mots « chocolate » et « soja », sans allergène déclaré (Galletas María)
    check(verdict(['gluten'], 'Harina de TRIGO 74%, azúcar, grasa de palma, chocolate, lecitina de soja') == 'check', 'liste en espagnol avec du blé : à vérifier')
    check(verdict(['milk', 'eggs'], 'Weizenmehl, Zucker, Butter, Vollmilchpulver, Eier') == 'check', 'liste en allemand avec lait et œufs : à vérifier')
    why = page.evaluate("""() => { const R = window.__RS; R.profile.sel = new Set(['gluten']); R.profile.words = []; R.profile.traces = false;
      return R.evaluate({ code:'2', product_name:'Brotchips', ingredients_text_fr:'Weizenmehl, Zucker, Butter, Salz', allergens_tags:[], traces_tags:[], categories_tags:[] }).check.join(' | '); }""")
    check('« Weizenmehl » (gluten ?)' in why, 'mot étranger : la raison nomme l\'allergène (' + why + ')')
    why2 = page.evaluate("""() => window.__RS.evaluate({ code:'3', product_name:'Keks', ingredients_text_fr:'Weizenmehl, Zucker, Salz, Wasser', allergens_tags:[], traces_tags:[], categories_tags:[] }).check.join(' | ')""")
    check('autre langue' in why2, 'liste illisible : le message dit qu\'elle est peut-être dans une autre langue (' + why2 + ')')
    why3 = page.evaluate("""() => { const R = window.__RS; R.profile.sel = new Set(['milk']);
      return R.evaluate({ code:'4', product_name:'Galleta', ingredients_text_fr:'harina, azúcar, chocolate, LECHE en polvo, sal', allergens_tags:[], traces_tags:[], categories_tags:[] }).check.join(' | '); }""")
    check('« LECHE » (lait ?)' in why3, 'mot étranger connu : la raison nomme aussi l\'allergène (' + why3 + ')')
    # 3.26 : la raison nomme l'allergène pour les mots moins connus
    def why(sel, ing, extra=None):
        prod = {'code': '5', 'product_name': 'Produit test', 'brands': 'Marque', 'ingredients_text_fr': ing, 'allergens_tags': [], 'traces_tags': [], 'categories_tags': []}
        prod.update(extra or {})
        return page.evaluate("""([sel, prod]) => { const R = window.__RS; R.profile.sel = new Set(sel); R.profile.words = []; R.profile.traces = false;
          const v = R.evaluate(prod); return v.check.concat(v.no).join(' | '); }""", [sel, prod])
    w = why(['mustard'], BASE + 'SENNEPSPULVER'); check('« SENNEPSPULVER » (moutarde ?)' in w, 'moutarde en norvégien : la raison nomme l\'allergène (' + w + ')')
    w = why(['fish'], BASE + 'raie'); check('« raie » (poisson ?)' in w, 'raie : la raison nomme le poisson (' + w + ')')
    w = why(['sulphites'], BASE + 'antioxydant : d_isulfite_ de potassium'); check('« disulfite »' in w, 'tiret bas au milieu du mot : mot reconstitué (' + w + ')')
    w = why(['eggs'], BASE + 'oeufs1 (20%)'); check('« oeufs »' in w, 'chiffre collé : le mot sans le chiffre (' + w + ')')
    # surlignage dans la fiche : le mot entier, sans le tiret bas ni le chiffre collé
    def marked(sel, ing):
        return page.evaluate("""([sel, ing]) => { const R = window.__RS; R.testProfile(sel); const d = document.createElement('div');
          d.innerHTML = R.renderIngredients(ing); return [...d.querySelectorAll('mark')].map(m => m.textContent).join(''); }""", [sel, ing])
    m = marked(['sulphites'], 'antioxydant : d_isulfite_ de potassium'); check(m == 'disulfite', 'surlignage de « d_isulfite_ » : ' + m)
    m = marked(['eggs'], 'farine, oeufs1 (20%), sucre1'); check(m == 'oeufs', 'surlignage de « oeufs1 » sans le chiffre : ' + m)
    m = marked(['mustard'], 'eau, SENNEPSPULVER, sel'); check(m == 'SENNEPSPULVER', 'surlignage d\'un mot étranger : ' + m)
    # « vegan » ou « sans » dans le nom n'annule plus que le lait et les œufs
    check(verdict(['peanuts'], BASE + 'rice protein, cocoa', {'product_name': 'Vegan Protein Bar Peanut Butter'}) == 'check', 'nom « Vegan … Peanut Butter » : à vérifier pour l\'arachide')
    check(verdict(['fish'], BASE + 'soja texturé', {'product_name': 'Thon végétal'}) == 'check', 'nom « Thon végétal » : à vérifier pour le poisson')
    check(verdict(['fish'], 'olives noires, huile, sel', {'product_name': 'Tapenade noire sans anchois'}) == 'ok', 'nom « … sans anchois » : pas de faux doute sur le poisson')
    check(verdict(['gluten'], 'farine de riz, eau, sel', {'product_name': 'Pain de mie sans gluten'}) == 'ok', 'nom « Pain de mie sans gluten » : pas de faux doute')
    check(verdict(['nuts'], 'jambon de porc, sel', {'product_name': 'Sugar Free Hazelnut Syrup'}) == 'check', 'nom « Sugar Free Hazelnut » : à vérifier pour les fruits à coque')
    check(verdict(['milk'], BASE + 'riz', {'product_name': 'Boisson végétale riz lait'}) == 'ok', 'nom « Boisson végétale … lait » : toujours pas de faux doute sur le lait')
    # 3.27 : « sans X » n'efface que le mot X lui-même, pas les autres indices du nom
    check(verdict(['fish'], 'olives noires, huile, sel', {'product_name': 'Rillettes de thon sans anchois'}) == 'check', 'nom « Rillettes de thon sans anchois » : à vérifier (thon)')
    check(verdict(['milk'], BASE + 'farine', {'product_name': 'Gâteau sans lait au beurre'}) == 'check', 'nom « Gâteau sans lait au beurre » : à vérifier (beurre)')
    check(verdict(['eggs'], BASE + 'farine', {'product_name': 'Gâteau sans oeuf mayonnaise'}) == 'check', 'nom « Gâteau sans œuf mayonnaise » : à vérifier (mayonnaise)')
    check(verdict(['milk'], BASE + 'farine', {'product_name': 'Gâteau sans lait'}) == 'ok', 'nom « Gâteau sans lait » : compatible')
    check(verdict(['lactose'], BASE + 'farine', {'product_name': 'Crème sans lactose'}) == 'ok', 'nom « Crème sans lactose » : pas de faux doute')
    check(verdict(['milk'], BASE + 'farine', {'product_name': 'Dessert vegan crème'}) == 'ok', 'nom « vegan » : toujours sans faux doute pour le lait')
    check(verdict(['gluten'], 'farine de riz', {'product_name': 'Biscuits sans gluten'}) == 'ok', 'nom « Biscuits sans gluten » : compatible')
    # rayons où l'allergène est presque toujours là
    check(verdict(['fish'], 'filets 100 %', {'categories_tags': ['en:frozen-fishes']}) == 'check', 'rayon poissons sans mot reconnu : à vérifier')
    check(verdict(['fish'], 'Filets sans peau de _bar_ BIO', {'categories_tags': ['en:fishes']}) == 'check', 'bar (rayon poissons) : à vérifier')
    check(verdict(['mustard'], 'eau, graines, vinaigre, sel', {'categories_tags': ['en:mustards']}) == 'check', 'rayon moutardes : à vérifier')
    check(verdict(['sulphites'], 'raisin', {'categories_tags': ['en:red-wines']}) == 'check', 'vin rouge sans sulfites écrits : à vérifier')
    check(verdict(['sulphites'], 'raisin', {'categories_tags': ['en:champagnes']}) == 'check', 'champagne sans sulfites écrits : à vérifier')
    check(verdict(['fish'], BASE + 'riz', {'categories_tags': ['en:rices']}) == 'ok', 'rayon sans garde-fou : compatible')
    check(not errs, 'aucune erreur JavaScript' + (': ' + '; '.join(errs[:3]) if errs else ''))
    b.close()
httpd.shutdown()
print('\n' + ('TOUT EST OK' if not FAIL else f'{len(FAIL)} ÉCHEC(S)'))
sys.exit(1 if FAIL else 0)
