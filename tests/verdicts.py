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
    # 3.28 : mots manquants
    ('gluten', 'farine', 'check'), ('gluten', 'nouilles', 'check'), ('gluten', 'ramen', 'check'), ('gluten', 'gnocchi', 'check'), ('gluten', 'panko', 'check'),
    ('gluten', 'tempura', 'check'), ('gluten', 'vermicelles', 'check'), ('gluten', 'pâtes alimentaires', 'check'), ('gluten', 'sablé', 'check'),
    ('gluten', 'pâte feuilletée', 'check'), ('gluten', 'tortilla', 'check'), ('gluten', 'pizza', 'check'),
    ('gluten', 'farine de maïs', 'ok'), ('gluten', 'farine de pois chiches', 'ok'), ('gluten', 'farine sans gluten', 'ok'),
    ('gluten', 'nouilles de riz', 'ok'), ('gluten', 'vermicelles de riz', 'ok'), ('gluten', 'pizza sans gluten', 'ok'), ('gluten', 'farine de sarrasin, farine de blé', 'check'),
    ('milk', 'crema', 'check'), ('milk', 'yogourt', 'check'), ('milk', 'yoghourt', 'check'), ('milk', 'laitage', 'check'), ('milk', 'laitages', 'check'),
    ('milk', 'tomme', 'check'), ('milk', 'présure', 'check'), ('milk', 'boursin', 'check'), ('milk', 'kéfyr', 'check'), ('milk', 'ricota', 'check'),
    ('eggs', 'aïoli', 'check'), ('eggs', 'ovomucoïde', 'check'), ('eggs', 'ovalbumin', 'check'), ('eggs', 'albumen', 'check'), ('eggs', 'sauce hollandaise', 'check'),
    ('nuts', 'orgeat', 'check'), ('nuts', 'amaretto', 'check'), ('nuts', 'cerneaux', 'check'), ('nuts', 'anacardes', 'check'),
    ('soybeans', 'natto', 'check'), ('soybeans', 'okara', 'check'), ('soybeans', 'sauce teriyaki', 'check'),
    ('crustaceans', 'tourteau', 'check'), ('crustaceans', 'bisque', 'check'), ('crustaceans', 'fruits de mer', 'check'),
    ('molluscs', 'pieuvre', 'check'), ('molluscs', 'couteaux', 'check'), ('molluscs', 'fruits de mer', 'check'), ('molluscs', 'seafood', 'check'),
    ('sesame', 'houmous', 'check'), ('sesame', 'zaatar', 'check'), ('mustard', 'sauce dijonnaise', 'check'),
    ('fish', 'mulet', 'check'), ('fish', 'carpe', 'check'), ('fish', 'brochet', 'check'), ('fish', 'pollock', 'check'), ('fish', 'sushi', 'check'), ('fish', 'basa', 'check'),
    ('fish', 'filet de lieu', 'check'), ('fish', 'lieu noir', 'check'), ('fish', 'lieu jaune', 'check'), ('fish', 'lieu (Pollachius virens)', 'check'),
    ('fish', 'à conserver dans un lieu frais et sec', 'ok'), ('fish', 'plie', 'ok'),
    # 3.28 : caractères invisibles, pleine chasse, codes HTML
    ('milk', 'l\u00adait', 'check'), ('milk', 'la\u200bit', 'check'), ('milk', '\uff4c\uff41\uff49\uff54', 'check'), ('eggs', '&oelig;ufs', 'check'),
    ('gluten', 'bl&eacute;', 'check'), ('milk', 'lait&nbsp;écrémé', 'check'),
    # 3.29 : invisible entre deux mots, « flour » seul, œufs écrits « euf »
    ('milk', 'lait\u200eécrémé', 'check'), ('milk', 'lait\u200bécrémé en poudre', 'check'), ('milk', 'sucre,lait\u2060écrémé', 'check'),
    ('milk', 'l\u00adait', 'check'), ('milk', 'la\u200eit', 'check'),
    ('gluten', 'organic flour', 'check'), ('gluten', 'flour', 'check'), ('gluten', 'wheat flour', 'check'), ('gluten', 'farine', 'check'),
    ('gluten', 'rice flour', 'ok'), ('gluten', 'corn flour', 'ok'), ('gluten', 'flour of rice', 'ok'), ('gluten', 'farine de riz', 'ok'),
    ('gluten', 'farine de maïs', 'ok'), ('gluten', 'farine de lentilles', 'ok'), ('gluten', 'farine de caroube', 'ok'),
    ('eggs', 'blanc euf', 'check'), ('eggs', 'euf', 'check'), ('eggs', 'eufs frais', 'check'), ('eggs', 'oeufe', 'check'), ('eggs', 'oeufq', 'check'),
    # 3.30 : « fruits à coque » écrit en toutes lettres, et mots manquants
    ('nuts', 'Peut contenir des traces de fruits à coque', 'check'), ('nuts', 'traces de fruit à coque', 'check'), ('nuts', 'fruits à coques', 'check'),
    ('nuts', 'fruit(s) à coque', 'check'), ('nuts', 'tree nuts', 'check'), ('nuts', 'may contain tree nuts', 'check'), ('nuts', 'frutos secos', 'check'),
    ('nuts', 'Nüsse', 'check'), ('nuts', 'Nuss', 'check'), ('nuts', 'Kokosnuss', 'ok'), ('nuts', 'noix de coco', 'ok'),
    ('nuts', 'fruits de mer, coques', 'ok'),
    ('crustaceans', 'crustaceans', 'check'), ('crustaceans', 'Krebse', 'check'), ('crustaceans', 'Langusten', 'check'), ('crustaceans', 'Flusskrebs', 'check'),
    ('crustaceans', 'krevety', 'check'), ('crustaceans', 'lagostim', 'check'),
    ('molluscs', 'molluscs', 'check'), ('molluscs', 'mollusks', 'check'), ('molluscs', 'calamares', 'check'), ('molluscs', 'Schnecken', 'check'),
    ('molluscs', 'conque', 'check'), ('molluscs', 'buccin', 'check'),
    ('eggs', 'mayo', 'check'), ('eggs', 'omelette', 'check'), ('eggs', 'eggnog', 'check'), ('eggs', 'albumin', 'check'), ('eggs', 'vejce', 'check'),
    ('eggs', 'albumine de lait', 'ok'), ('eggs', 'mayor', 'ok'),
    ('peanuts', 'ground nuts', 'check'), ('peanuts', 'ground nut oil', 'check'), ('peanuts', 'cacahouettes', 'check'), ('peanuts', 'arachis', 'check'),
    ('peanuts', 'earth nut', 'check'), ('peanuts', 'beer nuts', 'check'), ('peanuts', 'orzeszki ziemne', 'check'), ('peanuts', 'arašídy', 'check'),
    ('peanuts', 'amendoim', 'check'), ('peanuts', 'acide arachidonique', 'ok'),
    # 3.32 : crustacés et mollusques en anglais, allemand, italien, espagnol ; textes abîmés
    ('crustaceans', 'CRUSTACEAN SHELLFISH', 'check'), ('crustaceans', 'crustacean', 'check'), ('crustaceans', 'shellfish', 'check'),
    ('molluscs', 'shellfish', 'check'), ('molluscs', 'molluscan shellfish', 'check'), ('crustaceans', 'Meeresfrüchte', 'check'),
    ('molluscs', 'Meeresfrüchte', 'check'), ('crustaceans', 'frutti di mare', 'check'), ('molluscs', 'frutti di mare', 'check'),
    ('crustaceans', 'mariscos', 'check'), ('molluscs', 'mariscos', 'check'),
    ('molluscs', 'mollus ues', 'check'), ('crustaceans', 'CRUSTRCE>', 'check'), ('crustaceans', 'CREV T TE', 'check'),
    ('crustaceans', 'pizza crust', 'ok'), ('crustaceans', 'piecrust', 'ok'), ('crustaceans', 'croûte', 'ok'), ('molluscs', 'croûte, pizza crust', 'ok'),
    ('nuts', 'fruits de mer', 'ok'), ('nuts', 'shellfish', 'ok'), ('nuts', 'noix de coco', 'ok'), ('molluscs', 'fruits à coque', 'ok'),
    # 3.32 : mots rares
    ('eggs', 'ovoalbumine', 'check'), ('eggs', 'albumina', 'check'), ('eggs', 'ovoalbumina', 'check'), ('eggs', 'tiramisu', 'check'),
    ('peanuts', 'monkey nuts', 'check'), ('peanuts', 'goober', 'check'), ('peanuts', 'sauce satay', 'check'),
    ('nuts', 'fruits à écale', 'check'), ('nuts', 'nutella', 'check'), ('milk', 'emmenthal', 'check'), ('fish', 'rollmops', 'check'),
    ('eggs', 'albumine de lait', 'ok'), ('peanuts', 'acide arachidonique', 'ok'), ('milk', 'lait de coco', 'ok'), ('peanuts', 'beurre de cacao', 'ok'),
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
    # 3.40 : garde-fous par rayon pour le céleri (bouillons) et le sésame (houmous, pains burger)
    check(verdict(['celery'], BASE + 'sel, graisse de palme, exhausteur de goût, boeuf', {'product_name': 'Cube de bouillon Boeuf Ideal', 'categories_tags': ['en:bouillon-cubes']}) == 'check', 'cube de bouillon sans céleri lisible : à vérifier pour le céleri')
    check(verdict(['celery'], BASE + 'os de volaille', {'categories_tags': ['en:broths']}) == 'check', 'bouillon sans céleri lisible : à vérifier pour le céleri')
    check(verdict(['sesame'], BASE + 'pois chiches, citron, ail', {'categories_tags': ['en:hummus']}) == 'check', 'houmous sans sésame lisible : à vérifier pour le sésame')
    check(verdict(['sesame'], BASE + 'farine, levure', {'categories_tags': ['en:hamburger-buns']}) == 'check', 'pain burger sans sésame lisible : à vérifier pour le sésame')
    check(verdict(['celery'], BASE + 'carottes', {'categories_tags': ['en:soups']}) == 'ok', 'soupe sans céleri : pas de faux doute')
    check(verdict(['sesame'], BASE + 'farine, levure', {'categories_tags': ['en:breads']}) == 'ok', 'pain ordinaire : pas de faux doute pour le sésame')
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
    # 3.28 : allergènes déclarés avec une étiquette non standard
    TAGS = [('celery', 'en:Céleri'), ('sulphites', 'fr:Anhydride sulfureux et sulfites (E220)'), ('sulphites', 'fr:Dioxyde de soufre et sulfites'),
            ('sulphites', 'fr:disulfite de sodium'), ('peanuts', 'en:arachide'), ('milk', 'en:lait'), ('lactose', 'en:lait'), ('nuts', 'en:fruits à coque'),
            ('milk', 'en:MILK SOLIDS'), ('milk', 'fr:lait'), ('milk', 'de:milch'), ('milk', 'en:Milk'), ('milk', 'EN:MILK'), ('gluten', 'en:wheat'),
            ('nuts', 'en:tree-nuts'), ('gluten', 'en:cereals-with-gluten'), ('crustaceans', 'en:crustaceans-and-shellfish'), ('eggs', ' en:eggs '), ('gluten', 'fr:Et produits à base de ces céréales')]
    bad = [f'{k} / {t}' for k, t in TAGS if verdict([k], BASE + 'riz', {'allergens_tags': [t]}) != 'no']
    check(not bad, f'{len(TAGS)} étiquettes déclarées non standard : exclu' + ('' if not bad else ' :\n    ' + '\n    '.join(bad)))
    TRACES = [('milk', 'en:lait'), ('nuts', 'en:fruits-a-coque'), ('gluten', 'en:cereals-with-gluten'), ('crustaceans', 'en:crustaceans-and-shellfish'), ('milk', 'EN:Milk')]
    bad = [f'{k} / {t}' for k, t in TRACES if verdict([k], BASE + 'riz', {'traces_tags': [t]}) != 'check']
    check(not bad, f'{len(TRACES)} traces non standard : à vérifier' + ('' if not bad else ' :\n    ' + '\n    '.join(bad)))
    check(verdict(['milk'], BASE + 'riz', {'allergens_tags': ['en:none']}) == 'ok', 'étiquette « en:none » : compatible')
    check(verdict(['milk'], BASE + 'riz', {'allergens_tags': ['en:gluten']}) == 'ok', 'autre allergène déclaré : pas de faux doute')
    check(verdict(['milk'], BASE + 'riz', {'allergens_tags': 'en:milk,en:gluten'}) == 'no', 'étiquettes écrites en une seule chaîne : exclu')
    check(verdict(['milk'], BASE + 'riz', {'allergens_tags': ['en:zorglub']}) == 'check', 'étiquette inconnue : à vérifier')
    check(verdict(['milk'], BASE + 'riz', {'allergens_tags': ['fr:kiwi']}, ) != 'no', 'étiquette d\'un autre aliment : pas exclu')
    # 3.28 : plusieurs textes d'ingrédients sur la fiche
    check(verdict(['milk'], 'eau, sucre, sel, arôme', {'ingredients_text': 'water, sugar, milk powder, salt'}) == 'check', 'lait seulement dans le texte original : à vérifier')
    check(verdict(['milk'], 'eau, sucre, sel, arôme', {'ingredients_text': 'water, sugar, salt, flavour'}) == 'ok', 'deux textes sans allergène : compatible')
    check(verdict(['milk'], 'eau, sucre, sel, arôme', {'ingredients_text': 'eau, sucre, sel, arôme'}) == 'ok', 'deux textes identiques : compatible')
    check(verdict(['milk'], '', {'ingredients_text_fr': '', 'ingredients_text': '', 'ingredients_text_en': 'milk, water'}) == 'check', 'texte anglais seul : à vérifier')
    # 3.34 : produits réels de la base, texte tel que lu sur l'emballage (allergène, code-barres, nom, ingrédients) : jamais « Compatible »
    REELS = [
        # œufs : mot collé ou précédé de lettres en trop, mots étrangers
        ('eggs', '26002200', '6 Cannelés de Bordeaux', 'ln deqait, lait écrémé), poudre dlœufs entiers, arôme vanille. Produit'),
        ('eggs', '3178880003859', 'Petites couronnes du Roussillon anis', 'Farine de blé, sucre, huile de colza, oœufs entiers en poudre, anis en grains 3%'),
        ('eggs', '3596710445653', 'Bâtonnets', 'Eau, chair de poissons 28,9%, diphosphates, blanc dlœuf poudre, arômes (contient poissons et crustacés)'),
        ('eggs', '7613033960307', 'Bûche glacée framboisier', 'eau, sirop de glucose, sucre, huile végétale (coco), blanc dtœuf, lactose'),
        ('eggs', '3551610008766', 'Panés de colin d’alaska', 'COLIN d\'Alaska MSC 58,8%, eau, farine de BLÉ*, blanc dqŒUF*, sel, poivre*'),
        ('eggs', '8020083111112', 'Pesto à la Génoise', "huile d'olive vierae extra. basilic 37 %, fromaaes râpés (LAIT. sel, orésure. conservateur: Ivsozvme dlŒUF.éoaississant:E460)"),
        ('eggs', '8002710812005', 'Zanetti Grana Padano Dop', 'Mælk, salt, osteløbe, konserveringsmiddel: lysozym fra ÆG.'),
        ('eggs', '8011242120137', "Pasta fresca all'uovo", 'QD PÂTES FRAICHESAUXOEUFS ln rédients: semoule de BLÉ dur, farine de BLÉ tendre, 02tJFS (20%), eau.'),
        ('eggs', '9000000000001', 'Pâtes', 'semoule de blé dur, eau, oeufsfrais'),
        ('eggs', '9000000000002', 'Pâtes', 'semoule de blé dur, oeufsentiers, eau'),
        ('eggs', '9000000000003', 'Gâteau', 'farine, sucre, dioeuf, eau'),
        ('eggs', '9000000000004', 'Gaufre', 'farine, sucre, lysozyme dlŒUF, eau'),
        ('eggs', '9000000000005', 'Crème', 'lait, sucre, æggehvide, eau'),
        ('eggs', '9000000000006', 'Pâtes', 'Durum, eggehvite, vann'),
        ('eggs', '9000000000007', 'Tagliatelle', 'semola di grano duro, uova fresche 20%'),
        # moutarde, arachide, poisson, céleri
        ('mustard', '3700009202449', 'Betteraves rouges', "Be 'alcool, MOUTAR 'E de Dijon (eau, pomme de terre *épaississant tgomme BP - 56382 GUER CEDEX."),
        ('mustard', '3596710446964', 'Concombre au fromage blanc', 'Concombre 81 %huile .dealza fromage blanc vinaigrè de Dijon(eau2 graines .demutarde;vinaigre datcool, purée d\'ail'),
        ('mustard', '9000000000008', 'Sauce', 'eau, mostazay, sel'),
        ('peanuts', '3421557912122', 'Granola', "Fabriqué dans un atelier qui utilise d'autres fruits à coque, du soja, des graines de sésame, du lait et de larachide."),
        ('peanuts', '3421557501401', 'Corn Flakes', 'Maïs* 65,7%, sucre de canne* 24.1 % Fabriqué dans atetier qui utilise des produits (aitiers et de liarachide.'),
        ('peanuts', '9000000000009', 'Biscuit', 'farine, sucre, ETARACHIDES'),
        ('fish', '9000000000010', 'Sauce', 'eau, sel, poudre depoissons'),
        ('celery', '9000000000011', 'Épices', 'sel, celeryand pepper'),
        # sulfites
        ('sulphites', '78230477', 'Abricots secs', 'abricots secs, conservateur: dioxide sulphurique)'),
        ('sulphites', '01583328', 'Dried mango', 'Dried mango, preservative sodium metabisulphates'),
        ('sulphites', '40893150', 'Soft apricots', 'Partially rehydrated drled pltted aprlcots 87 % Dried Apricots, Preservative: Sulphur Dloxlde; Water, Acids: Malic Acid'),
        ('sulphites', '5013635410811', 'Lemon Juice', 'lemon juice from concentrate (99.98%), preservative: potassium metabisulphate (0.02%)'),
        ('sulphites', '76106750', 'Jus de citron', 'Jus de citron 98.86%, huile essentielle de citron, acide citrique. Conservateur : métabisulfique de potassium.'),
        ('sulphites', '3512030017196', "Salade de pâtes à l'italienne", 'tomate cerise 19%, condiment balsamique blanc (vinaigre de vin, moût de raisin, conservateur : métabisul - fite de potassium), poivre blanc'),
        ('sulphites', '3760183292247', 'Mini financiers Orange', 'écorces d\'orange confites 8,6%(2) (sirop de glucose - fructose, correcteur d\'acidité : acide citrique, conservateur : anhydride sulfurique), stabilisant : sorbitol'),
        ('sulphites', '7610442255598', 'Cocosstängel', 'Cocos, sucre, conservateur (sulfure), origine: thailande'),
        ('sulphites', '8850161155079', 'Oriental chef coconut milk', 'COCO, EAU, METABISULFIDE DE SODIUM'),
        ('sulphites', '0206753037069', 'Pizza Saumon', "persillade (huile d'olives, persil, pulpe d'ail (sel, ail, anhydre de sulfure); eau; citron"),
        ('sulphites', '2869864040144', 'Queues de crevettes', 'ELABORÉ FRANCE : CREVETTES. sel. antioxydant tE223, acidifiant Sans colorant'),
        ('sulphites', '3182384050219', 'Melfor côté balsamique', "FR INGRÉDHTS : Vinaigre d'alcooly vinagre balsamique de tantes colorants: E150c, d, consentateurs : suPlfites Eà20 consomerde référenceavantladaie"),
        ('sulphites', '9000000000012', 'Fruits secs', 'abricots, acide sulfurique'),
        ('sulphites', '9000000000013', 'Fruits secs', 'abricots, conservateur : sulphurique'),
        ('sulphites', '9000000000014', 'Fruits secs', 'abricots, metabisulphate de sodium'),
        ('sulphites', '9000000000015', 'Fruits secs', 'abricots, anhydride sulfurique'),
        # crustacés et mollusques en allemand
        ('crustaceans', '5997523313050', 'CUP NOODLES Curry', 'Nudeln 77,6% [WEIZENMEHL, Palmöl, Kochsalz], Gewürze (SELLERIE). Kann Spuren von Krebstieren, Fisch, Weichtieren und Sesam enthalten.'),
        ('molluscs', '5997523313050', 'CUP NOODLES Curry', 'Nudeln 77,6% [WEIZENMEHL, Palmöl, Kochsalz], Gewürze (SELLERIE). Kann Spuren von Krebstieren, Fisch, Weichtieren und Sesam enthalten.'),
        ('crustaceans', '9000000000016', 'Suppe', 'Wasser, Salz, Schalentiere'),
        ('molluscs', '9000000000017', 'Suppe', 'Wasser, Salz, Schalentiere'),
        # nom du produit lu avec les mots d'une autre langue (ingrédients sans mot connu)
        ('crustaceans', '20191672', 'Gamba blanca del Mediterráneo', '100 % viande bovine.'),
        ('gluten', '32328585', 'Trigo Espelta 0% Azucares', 'ORGANIC CORN, ORGANIC SUNFLOWER OIL'),
        ('peanuts', '3222475893421', 'Thoms speciale pindakaas', 'Pain de mie 49,3% (eau - sel)'),
        ('nuts', '26042954', 'Gefüllte Oliven mit Mandeln (Penny) / Viande Hachée pur boeuf (Aldi)', '100 % viande bovine.'),
        ('peanuts', '20292133', 'Bio-Fruchtschnitte Dattel-erdnuss', 'viande de porc, sel, muscade'),
        ('sesame', '8000744000344', 'Pagnottine con sesamo', 'Da consu sa sul retro re qualche gl LK rre hydr sunflowe flour.'),
        ('sesame', '9000000000018', 'Pain au sesamo', 'farine, eau'),
        # soja slave ou scandinave
        ('soybeans', '7622300479107', 'Choco Dessert', 'Šećer, voda, kakaov maslac, emulgatori (sojini lecitini, E476, E471), sol'),
        ('soybeans', '8007990405985', 'Hulala whipping', 'Voda, sladkor (11%), stabilizatorji: E420ii, sojin lecitin (E322), E472b, sol'),
        ('soybeans', '4056489751403', 'Protein pancake', 'zabliszt, tejcsokoládé (cukor, kakaóvaj, emulgeálószer: lecitinek /szója/; természetes vaniliaaroma)'),
        ('soybeans', '7622300248987', 'Oboy', 'Sukker, 18% fettredusert kakao (med emulgator soyalecitin), druesukker, salt'),
        ('soybeans', '4001724029526', 'Double Peppetoni Pizza', 'Hvetemel, vann, rapsolje, soyasaus (vann, soyabønner, salt, hvetemel), byggmaltekstrakt'),
        ('soybeans', '9000000000019', 'Snack', 'mąka, sojový extrakt, sůl'),
        # faux amis qui restent compatibles
        ('sulphites', '9000000000020', 'Sel', 'sulfate de fer, sulfate de zinc, sulfate de cuivre, sel'),
        ('eggs', '9000000000021', 'Plat', 'viande de bœuf 20%, boeuf, sel'),
        ('eggs', '9000000000022', 'Plat', 'Jœuf, sel'),
        # 3.35 : mots abîmés par la lecture de l'étiquette (produits réels de la base)
        ('eggs', '3173310023810', 'Brioche', 'farine de blé, sucre, OEUPS frais 18%, beurre, sel'),
        ('eggs', '2404000800864', 'Madeleine', 'farine, sucre, oeurfs, beurre, sel'),
        ('milk', '10319673', 'Brioche', 'farine de blé, sucre, beurte, sel'),
        ('nuts', '3335440225117', 'Financiers', 'sucre, poudre d\'AMANOES 14%, farine, blancs d\'oeufs'),
        ('nuts', '3549170003031', 'Financiers', 'sucre, poudre d\'amende 15%, farine'),
        ('mustard', '5400501115015', 'Mayonnaise', 'huile de colza, eau, moutrade, sel'),
        ('mustard', '2655989020075', 'Merguez', 'viande de boeuf, sel, épices, MOUTRROE'),
        ('fish', '3257630765435', 'Tapenade', 'olives noires, câpres, anchols, huile d\'olive'),
        ('celery', '3770009733069', 'Velouté', 'eau, légumes, celeni, sel'),
        ('sulphites', '3760158961017', "Confit d'oignons", 'oignons, sucre, vinaigre, conservateur (sufite)'),
        ('sesame', '0250023008662', 'Pain au Son', 'farine, son, SESAHE, sel'),
        ('peanuts', '5025324009169', 'Protein Bar', 'protéines, cacahoutto, ca±uètes, sel'),
        ('gluten', '3292070006724', 'Houmous', 'pois chiches, tahin, citron, glutent, sel'),
        # autres variantes abîmées : toujours « À vérifier »
        ('eggs', '9000000000031', 'Gâteau', 'farine, yolk, sel'),
        ('milk', '9000000000032', 'Crème', 'eau, Sahne, sel'),
        ('milk', '9000000000033', 'Dessert', 'eau, Joghurt, sel'),
        ('milk', '9000000000034', 'Dessert', 'eau, mlieko, sel'),
        ('milk', '9000000000035', 'Poudre', 'eau, lactalbumin, sel'),
        ('milk', '9000000000036', 'Poudre', 'eau, lactccerum, sel'),
        ('nuts', '9000000000037', 'Biscuit', 'farine, noiseties, sel'),
        ('mustard', '9000000000038', 'Sauce', 'eau, moufrde, sel'),
        ('mustard', '9000000000039', 'Sauce', 'eau, nwutarde, sel'),
        ('mustard', '9000000000040', 'Sauce', 'eau, esoutarde, sel'),
        ('mustard', '9000000000041', 'Sauce', 'eau, moutari, sel'),
        ('mustard', '9000000000042', 'Sauce', 'voda, hořčice, sůl'),
        ('celery', '9000000000043', 'Soupe', 'eau, celei, sel'),
        ('celery', '9000000000044', 'Soupe', 'Wasser, Zeller, Salz'),
        ('sulphites', '9000000000045', 'Fruits secs', 'abricots, disufite de sodium'),
        ('sulphites', '9000000000046', 'Fruits secs', 'abricots, conservateur : sultes'),
        ('sulphites', '9000000000047', 'Fruits secs', 'abricots, bisulfate de sodium'),
        ('sesame', '9000000000048', 'Pain', 'farine, sesaee, sel'),
        ('sesame', '9000000000049', 'Pain', 'farine, sisame, sel'),
        ('peanuts', '9000000000050', 'Biscuit', 'farine, arachde, sel'),
        ('peanuts', '9000000000051', 'Biscuit', 'farine, arachldes, sel'),
        ('gluten', '9000000000052', 'Pain', 'eau, glutens, sel'),
        ('lupin', '9000000000053', 'Farine', 'farine, ŁUBIN, sel'),
        ('lupin', '9000000000054', 'Farine', 'mąka, łubin, sól'),
        ('nuts', '9000000000055', 'Biscuit', 'farine, amendes, sel'),
        # faux amis qui restent compatibles (3.35)
        ('eggs', '9000000000060', 'Poulet', 'poularde, sel'),
        ('mustard', '9000000000061', 'Café', 'mouture fine, moulues, sel'),
        ('mustard', '9000000000062', 'Sauce', 'pulpe de tomate, recette de la maison'),
        ('sulphites', '9000000000063', 'Sel', 'sulfate de magnésium, sulfate de calcium, sel'),
        ('milk', '9000000000064', 'Curry', 'lait de coco, sel'),
        # « sans moutarde » / « sans sulfite » restent « À vérifier » (prudence voulue, pas de « sans » qui assouplit)
        ('mustard', '9000000000065', 'Sauce', 'huile, sel, sans moutarde'),
        ('sulphites', '9000000000066', 'Fruits secs', 'abricots, sans sulfite'),
        ('nuts', '9000000000067', 'Gâteau', 'farine, sucre, amandes de mer'),
        ('eggs', '9000000000068', 'Soupe', 'poularde, pulpe, recette, mouture'),
        # 3.36 : ingrédients en roumain, croate, portugais, nordique, mots collés ou mal lus (produits réels de la base)
        ('mustard', '5900783009496', 'Heinz Seriously GOOD Mayonnaise Sauce', 'M RO Sos de maioneză cu 70 % conţinut de grăsime. Ingrediente: Ulei de rapiţă 68%, apă, gălbenuș de ou pasteurizat * 5%, otet, zahăr, amidon, sare, seminte de mustar condimente, antioxidant (calciu disodic EDTA). *din ouă de găini crescute în aer liber. Ulei de rapita şi ou: origine UE şi din afara UE A se consuma de preferinţă înainte de: vezi capac. După deschidere pastrati la frigider. EL Σάλτσα μαγιονέζας. Συστατικά: Κραμβέλαιο 68%, νερό, παστεριωμένοι κρόκοι αυγού* 5%, ξύδι από αλκοόλη, ζάχαρη, άμυλο, αλάτι, σπόροι μουστάρδας μπαχαρικά αντιοξειδωτικό (άλας του ΕΟΤΑ με ασβεστιονάτριο). *απ'),
        ('eggs', '5900783009496', 'Heinz Seriously GOOD Mayonnaise Sauce', 'M RO Sos de maioneză cu 70 % conţinut de grăsime. Ingrediente: Ulei de rapiţă 68%, apă, gălbenuș de ou pasteurizat * 5%, otet, zahăr, amidon, sare, seminte de mustar condimente, antioxidant (calciu disodic EDTA). *din ouă de găini crescute în aer liber. Ulei de rapita şi ou: origine UE şi din afara UE A se consuma de preferinţă înainte de: vezi capac. După deschidere pastrati la frigider. EL Σάλτσα μαγιονέζας. Συστατικά: Κραμβέλαιο 68%, νερό, παστεριωμένοι κρόκοι αυγού* 5%, ξύδι από αλκοόλη, ζάχαρη, άμυλο, αλάτι, σπόροι μουστάρδας μπαχαρικά αντιοξειδωτικό (άλας του ΕΟΤΑ με ασβεστιονάτριο). *απ'),
        ('mustard', '5941486004791', 'LaMinut Muștar Iute', 'CONSERVANTI LaMinut, Mustar iute cu îndulcitor. Ingrediente: apà, boabe de mustar (16,5%), oțet din vint sare, agent de îngropre (gumâ de xantan), acidifiant (acid citric), condimente si extracte de condimente (extract de Chilli 0,196), colorant (beta caroten), aromàt îndulcitor (sucralozà).'),
        ('eggs', '5948710006705', 'Cordon bleu', 'file de piept de pui 62%, sunca de curcan 10% (carne de curcan 80%, apa, amidon de tapioca, sare cu nitrit, difosfat de sodiu, maltodextrina, dextroza, acid ascorbic), pesmet, branza gouda 7,5% (lapte), oua, ulei de rapita, apa, sare, sirop uscat de glucoza'),
        ('gluten', '5941341020904', 'Pateu Vegetal cu ciuperci', "Apă, ulei vegetal nehidrogenat de floarea-soarelui, ciuperci (5%), proteină vegetală din soia, amidon din grâu, amidon din porumb, sare iodată, stabilizatori polifosfati; emulsifianti: stearoil 2-lactilat de sodiu, esteri citrici ai mono-şi digliceridelor cu acizi graşi; arome, sirop de glucoză, condimente, mustar, ţelină, potenţiatori de aromă: glutamat monosodic, 5'-ribonucleotide disodice; legume deshidratate (tomate, ceapă, usturoi), agent de îngroşare: gumǎ xantan; antioxidanţi: ascorbat de sodiu, acid citric; agenţi gelatinizanti: caragenan, dorură de potasiu; coloranti: caramel, extract"),
        ('mustard', '5941341020904', 'Pateu Vegetal cu ciuperci', "Apă, ulei vegetal nehidrogenat de floarea-soarelui, ciuperci (5%), proteină vegetală din soia, amidon din grâu, amidon din porumb, sare iodată, stabilizatori polifosfati; emulsifianti: stearoil 2-lactilat de sodiu, esteri citrici ai mono-şi digliceridelor cu acizi graşi; arome, sirop de glucoză, condimente, mustar, ţelină, potenţiatori de aromă: glutamat monosodic, 5'-ribonucleotide disodice; legume deshidratate (tomate, ceapă, usturoi), agent de îngroşare: gumǎ xantan; antioxidanţi: ascorbat de sodiu, acid citric; agenţi gelatinizanti: caragenan, dorură de potasiu; coloranti: caramel, extract"),
        ('celery', '5941341020904', 'Pateu Vegetal cu ciuperci', "Apă, ulei vegetal nehidrogenat de floarea-soarelui, ciuperci (5%), proteină vegetală din soia, amidon din grâu, amidon din porumb, sare iodată, stabilizatori polifosfati; emulsifianti: stearoil 2-lactilat de sodiu, esteri citrici ai mono-şi digliceridelor cu acizi graşi; arome, sirop de glucoză, condimente, mustar, ţelină, potenţiatori de aromă: glutamat monosodic, 5'-ribonucleotide disodice; legume deshidratate (tomate, ceapă, usturoi), agent de îngroşare: gumǎ xantan; antioxidanţi: ascorbat de sodiu, acid citric; agenţi gelatinizanti: caragenan, dorură de potasiu; coloranti: caramel, extract"),
        ('gluten', '4000522009747', 'Stickletti Cartofi', 'Amidon din cartofi (30%), făină de GRÂU, ulei de rapiţă, cartofi pudră (15 %), sare, extract de drojdie, produs din ZER (LAPTE), aromă, agent de creştere (hidrogenocarbonat de sodiu), condiment, colorant (curcumină). Poate conține urme de SEMINTE DE SUSAN si SOIA.'),
        ('sesame', '4000522009747', 'Stickletti Cartofi', 'Amidon din cartofi (30%), făină de GRÂU, ulei de rapiţă, cartofi pudră (15 %), sare, extract de drojdie, produs din ZER (LAPTE), aromă, agent de creştere (hidrogenocarbonat de sodiu), condiment, colorant (curcumină). Poate conține urme de SEMINTE DE SUSAN si SOIA.'),
        ('gluten', '59939788', 'Choco Wafer', 'Zahăr, făină de GRAU, unt de cacao, LAPTE praf degresat, masă de cacao, grăsimi vegetale (palmier, cocos, în proporţii variabile), zer praf (din LAPTE), grăsime din LAPTE, ulei de rapiță, dextroză, făină de SOIA, pastă de ALUNE DE PADURE 0,8 %, cacao cu conținut redus de grăsime, emulsifiant (lecitine din SOIA), agent de afânare (E500), sare, arome. POATE CONTINE OUA.'),
        ('eggs', '59939788', 'Choco Wafer', 'Zahăr, făină de GRAU, unt de cacao, LAPTE praf degresat, masă de cacao, grăsimi vegetale (palmier, cocos, în proporţii variabile), zer praf (din LAPTE), grăsime din LAPTE, ulei de rapiță, dextroză, făină de SOIA, pastă de ALUNE DE PADURE 0,8 %, cacao cu conținut redus de grăsime, emulsifiant (lecitine din SOIA), agent de afânare (E500), sare, arome. POATE CONTINE OUA.'),
        ('nuts', '59939788', 'Choco Wafer', 'Zahăr, făină de GRAU, unt de cacao, LAPTE praf degresat, masă de cacao, grăsimi vegetale (palmier, cocos, în proporţii variabile), zer praf (din LAPTE), grăsime din LAPTE, ulei de rapiță, dextroză, făină de SOIA, pastă de ALUNE DE PADURE 0,8 %, cacao cu conținut redus de grăsime, emulsifiant (lecitine din SOIA), agent de afânare (E500), sare, arome. POATE CONTINE OUA.'),
        ('sesame', '7891000060421', 'Nesfit Gergelim', '_farinha de trigo integral 29%, _farinha de trigo 20%_, _farinha de triticale 8.5%_ enriquecidas com ferro e ácido fólico, óleo vegetal, _gergelim 2%_, açúcar invertido, açúcar, sal, fermentos químicos bicarbonato de amônio, fosfato monocálcico, bicarbonato de sódio, emulsificantes: lecitina de soja, ésteres de ácido diacetil tartárico e ácidos graxos com poliglicerol e mono e diglicerídeos de ácidos graxos, melhorador de farinha: metabissulfito de sódio.'),
        ('eggs', '4061463022189', 'Pralinen', 'Zucker, Kakaobutter, Kakaomasse, Mandeln, Magermilchpulver, Vollmilchpulver, Butterreinfett, Feuchthaltemittel: Sorbitsirup, Invertase; Haselnüsse, Invertzuckersirup, Eierlikör, Kokosnussöl, Glukosesirup, Walnüsse, Gin, schokoliertes Birnen-Karamell-Granulat (Zucker, Kakaobutter, Vollmilchpulver, Kakaomasse, Butterreinfett, Glukosesirup, getrocknetes Birnenfruchtpulver, Maisstärke, Aromen, Salz, Emulgator: Lecithine (Soja)), pflanzliche Fette (Palm, Shea), Kondensmilch, Rum, Emulgator: Lecithine (Soja); Marc de Champagne, Oran - genspirituose, Mandellikör, Maismehl, Aromen, Säuerungsmittel: Ci'),
        ('eggs', '8055349400143', 'Panettone', 'me naturel de Cocoo butter, Emulsifyng agent: Soyo )ecjthin, Noturol Energi Ooyour)- Butter Sugar fresh ggyolk - Naturolyeost (conjoins naturelle Isdesocides gras Emulsifyng agent: Mono-dygljcerides of fotty ocids - Invert-sugor Whole fresh pasteurized milk - Salt'),
        ('milk', '3034910344807', 'Saucisson sec', 'viande de porc VPF, sel, lactoss, épices, rhum, sucre, dextrose, conservateur: nitrate de potassium, ferments, boyau naturel de porc.'),
        ('nuts', '3335440225414', 'Financiers  à la pomme', "SUcre, blanc dlOEClF de France (stabilisants . gomme de guat BEURRE de France, poudre dlAMANDES 15%1 farine de miel France 9%, cubes de pomme 6%1 pomme en poudre 3% (porr,T'e 75%, amidon de maïs), arôme naturel pomme Présence possible d'arachides. valeurs nutrltfrznelles pour 100g : Energie 1705 KS-408 KCa\\v grasses 2 lg dont acides gras saturés 9, lg Glucides dont sucres 35g ; Protéines Sel A CONSOMMER DE PREFERENCE AVANT LE : 11%412018"),
        ('milk', '4260363480444', 'Porridge Vanille', "tq&ts: defatted soy semolina*, whole milkpowdett oat flakes* defattedso!lce natural flavour, thickener (guar gum*), natura/ bourbon vanl/a 'Vic, EC Control System"),
        ('fish', '5410724320011', 'Bagels', 'SaunonAtlantiqUe 97% Ecosse), sel, fumée de bois de hêtre'),
        ('fish', '4897878000081', 'Ramen Noodles Shrimp Flavour 100G', "NOUILLES'. FARINE DE BLÉ, HUILE DE P HEWÉTAPHOSPHATE DE SODIUM, CARBONATE DE pot8SllJ)/, TRIPOLYPHOSPHATE DE SODIUM, CARBONATE DE SODIUM, DEXTRINE, ALGINATE DE SODIUM, GOMME GUAR, PHOSPHATE DE SODIUM, TOCOPHÉROLS, PYROPHOSPHATE DE TÉTRASODIUM, DIASCORBYLE, THÉ VERT EN POUDRE. BASE DE SOUPE: SELTOUDRE DE FRUITS DE MER (CREVETTE, COQUILLE SAINT-JACQUESIANCHOIS), GLUTAMATE DE MONOSODIUM, AMIDON DE TAPIOCA, SUCRE, PROTÉINE DE SOJA HYDROLYSÉE, DEXTROSE, SAUCE SOJA EN POUDRE (GRAINES DE SOJA, BLÉ, SEL), POUDRE DIOIGNoN, MALTODEXTRINE, DE LEVURE, COLOMNT OIGNON VERT DÉSHYDRATÉ, POUDRE DIAIL, PIMENT P"),
        ('milk', '7622210741530', 'Daim Bites', 'Närngsvärde /Næringsværdi / Ravintoarvot Mjölkchoklad med mandelkrokant (23 %) och corn flakes, Ingredienser: %* 100 g 25g Socker, kakaosmör, rostade majsflingor Energi/Energiaa 725 g 10 % (majs, socker, salt, maltextrakt från 2134 kJ'),
        ('nuts', '7622210741530', 'Daim Bites', 'Närngsvärde /Næringsværdi / Ravintoarvot Mjölkchoklad med mandelkrokant (23 %) och corn flakes, Ingredienser: %* 100 g 25g Socker, kakaosmör, rostade majsflingor Energi/Energiaa 725 g 10 % (majs, socker, salt, maltextrakt från 2134 kJ'),
        ('gluten', '5701318298985', 'Kartoffelsalat', 'DK INGREDIENSER: Kogte kartofler (Tyskland) 60%, vand, rapsolie, løg, eddike, sukker, majs - og hvedestivelse, salt, tørret purløg, æggeblomme, surhedsregulerende middel (E 262), krydderiblan - ding (salt, krydderier, krydderiekstrakter, gærekstrakt, maltodextrin), konserve - ringsmiddel (E 202, E 211), krydderiekstrakt, sennep (vand, sennepsfre, eddike, salt, krydderier), fortykningsmiddel (E 412, E 415), hydrolyseret raps - og majsprotein, estragonekstrakt. OPBEVARING: Ved højst +8°C. Efter åbning: 3-5 dage i køleskab. EMBALLAGE: Skylles og sorteres som hård plast. FORBRUGERKONTAKT: www.coop'),
        ('eggs', '5701318298985', 'Kartoffelsalat', 'DK INGREDIENSER: Kogte kartofler (Tyskland) 60%, vand, rapsolie, løg, eddike, sukker, majs - og hvedestivelse, salt, tørret purløg, æggeblomme, surhedsregulerende middel (E 262), krydderiblan - ding (salt, krydderier, krydderiekstrakter, gærekstrakt, maltodextrin), konserve - ringsmiddel (E 202, E 211), krydderiekstrakt, sennep (vand, sennepsfre, eddike, salt, krydderier), fortykningsmiddel (E 412, E 415), hydrolyseret raps - og majsprotein, estragonekstrakt. OPBEVARING: Ved højst +8°C. Efter åbning: 3-5 dage i køleskab. EMBALLAGE: Skylles og sorteres som hård plast. FORBRUGERKONTAKT: www.coop'),
        ('peanuts', '4751008578027', 'Muesli nutty crunch', 'EE Kröbe müsli pähklitega. Koostisosad: täistera kaerahelbed 48%, suhkur, palmiöli, röstitud hakitud sarapuupähklid 5%, täaisteranisuklid, risi ekstrudaat (risijahu suhkur, nisugluteen, odra - ja nisulinnasejahu, sool, odralinnaseekstrakt), röstitud máapähklid 4%, röstitud nisuhelbed (nisu, suhkur, sool, odralinnaseekstrakt), rivitud kookospähkel, glükoosi-fruktoosisiirup, kergitusaine E500, karamellsirup, Tooduslikud lõhna - ja maitseained. Võib sisaldada piima, soja ja seesamiseemnete jälgi. Parim enne: vaata pakendilt. Hóida kuivas kohas. Tarbida piima, jogurti või keefiriga. Valmistatud Po'),
        ('fish', '7037610027045', 'Toro Bergensk Fiskesuppe 81g', 'hvetemel, skummetmelk, maisstivelse, salt, fisk 7 %(sei), sukker, gulrot 4 %, løk, aroma, purre 3 %, sellerirot, rapsolje, egg, syre( sitronsyre), gressløk, fargestoff ( karotener).'),
        ('mustard', '9000000000100', 'Test', 'sucre, mustar, sel'),
        ('mustard', '9000000000101', 'Test', 'sucre, muștar, sel'),
        ('celery', '9000000000102', 'Test', 'sucre, telină, sel'),
        ('celery', '9000000000103', 'Test', 'sucre, telina, sel'),
        ('eggs', '9000000000104', 'Test', 'sucre, oua, sel'),
        ('eggs', '9000000000105', 'Test', 'sucre, ouă, sel'),
        ('eggs', '9000000000106', 'Test', 'sucre, galbenuș de ou, sel'),
        ('gluten', '9000000000107', 'Test', 'sucre, grâu, sel'),
        ('gluten', '9000000000108', 'Test', 'sucre, faină de grâu, sel'),
        ('peanuts', '9000000000109', 'Test', 'sucre, arahide, sel'),
        ('sesame', '9000000000110', 'Test', 'sucre, susan, sel'),
        ('sesame', '9000000000111', 'Test', 'sucre, tragove susama, sel'),
        ('sesame', '9000000000112', 'Test', 'sucre, gergelim, sel'),
        ('nuts', '9000000000113', 'Test', 'sucre, alune, sel'),
        ('nuts', '9000000000114', 'Test', 'sucre, nuci, sel'),
        ('sulphites', '9000000000115', 'Test', 'sucre, dioxid de sulf, sel'),
        ('eggs', '9000000000116', 'Test', 'sucre, eierlikör, sel'),
        ('eggs', '9000000000117', 'Test', 'sucre, eggpowder, sel'),
        ('eggs', '9000000000118', 'Test', 'sucre, eggyolk, sel'),
        ('eggs', '9000000000119', 'Test', 'sucre, mayonnais, sel'),
        ('eggs', '9000000000120', 'Test', 'sucre, eiern, sel'),
        ('eggs', '9000000000121', 'Test', 'sucre, eierzeugnissen, sel'),
        ('milk', '9000000000122', 'Test', 'sucre, lactoss, sel'),
        ('milk', '9000000000123', 'Test', 'sucre, lactosc, sel'),
        ('milk', '9000000000124', 'Test', 'sucre, lactosk, sel'),
        ('milk', '9000000000125', 'Test', 'sucre, lactosœ, sel'),
        ('nuts', '9000000000126', 'Test', 'sucre, dlAMANDES, sel'),
        ('milk', '9000000000127', 'Test', 'sucre, milkpowder, sel'),
        ('nuts', '9000000000128', 'Test', 'sucre, nussfrüchten, sel'),
        ('nuts', '9000000000129', 'Test', 'sucre, ořechy, sel'),
        ('nuts', '9000000000130', 'Test', 'sucre, mandorlato, sel'),
        ('fish', '9000000000131', 'Test', 'sucre, saunon, sel'),
        ('fish', '9000000000132', 'Test', 'sucre, JACQUESIANCHOIS, sel'),
        ('milk', '9000000000133', 'Test', 'sucre, maito, sel'),
        ('milk', '9000000000134', 'Test', 'sucre, maitojauhe, sel'),
        ('milk', '9000000000135', 'Test', 'sucre, mjölkpulver, sel'),
        ('milk', '9000000000136', 'Test', 'sucre, mjölkchoklad, sel'),
        ('milk', '9000000000137', 'Test', 'sucre, mjølk, sel'),
        ('milk', '9000000000138', 'Test', 'sucre, piim, sel'),
        ('milk', '9000000000139', 'Test', 'sucre, fløde, sel'),
        ('milk', '9000000000140', 'Test', 'sucre, flode, sel'),
        ('gluten', '9000000000141', 'Test', 'sucre, hvede, sel'),
        ('gluten', '9000000000142', 'Test', 'sucre, vetestärkelse, sel'),
        ('gluten', '9000000000143', 'Test', 'sucre, havregryn, sel'),
        ('eggs', '9000000000144', 'Test', 'sucre, æggeblomme, sel'),
        ('eggs', '9000000000145', 'Test', 'sucre, aeggeblomme, sel'),
        ('eggs', '9000000000146', 'Test', 'sucre, egge - plomme, sel'),
        ('eggs', '9000000000147', 'Test', 'sucre, eggeplomme, sel'),
        ('fish', '9000000000148', 'Test', 'sucre, fiskesuppe, sel'),
        ('fish', '9000000000149', 'Test', 'sucre, torsk, sel'),
        ('fish', '9000000000150', 'Test', 'sucre, tonfisk, sel'),
        ('fish', '9000000000151', 'Test', 'sucre, lohi, sel'),
        ('peanuts', '9000000000152', 'Test', 'sucre, jordnøtter, sel'),
        ('peanuts', '9000000000153', 'Test', 'sucre, jordnötter, sel'),
        ('peanuts', '9000000000154', 'Test', 'sucre, maapähklid, sel'),
        ('peanuts', '9000000000155', 'Test', 'sucre, kikiriki, sel'),
        ('nuts', '9000000000156', 'Test', 'sucre, mandelkrokant, sel'),
        ('nuts', '9000000000157', 'Test', 'sucre, nøtter, sel'),
        ('nuts', '9000000000158', 'Test', 'sucre, nødder, sel'),
        ('nuts', '9000000000159', 'Test', 'sucre, nötter, sel'),
        ('nuts', '9000000000160', 'Test', 'sucre, mandle, sel'),
        ('fish', '9000000000300', 'Test', 'sucre, relax, sel'),
        ('mustard', '9000000000301', 'Test', 'sucre, relax, sel'),
        ('fish', '9000000000302', 'Test', 'sucre, eggplant, sel'),
        ('eggs', '9000000000303', 'Test', 'sucre, eggplant, sel'),
        ('eggs', '9000000000304', 'Test', 'sucre, Eierschwammerl, sel'),
        ('fish', '9000000000305', 'Test', 'sucre, coquille Saint-Jacques, sel'),
        # 3.40 : textes néerlandais, suédois, danois, norvégien, allemand (Chinese tomatensoep 8714100721483 : « mie », « El-EIWIT », « ROOM »)
        ('milk', '9000000000400', 'Test', 'Water, suiker, room 10%, boter, glucosestroop, zout'),
        ('eggs', '9000000000401', 'Test', 'Groenten 40%, water, mie 5% (tarwe), gedroogd eiwit, zout'),
        ('gluten', '9000000000402', 'Test', 'Water, koekjes, wafel, pannenkoek, zout'),
        ('milk', '9000000000403', 'Test', 'Vatten, socker, grädde 20%, smör, salt'),
        ('gluten', '9000000000404', 'Test', 'Vatten, vetemjöl 40%, socker, havre, salt'),
        ('eggs', '9000000000405', 'Test', 'Vatten, ägg 10%, salt, socker'),
        ('gluten', '9000000000406', 'Oatly Havredrikk Sjokolade', 'vann, havre 10 %, rapsolje, kakao, salt'),
        ('gluten', '9000000000407', 'Test', 'Water, tarwebloem 30%, zout, gist, paneermeel, beschuit'),
        ('gluten', '9000000000408', 'Test', 'Wasser, Nudeln 30%, Brot, Salz'),
        ('gluten', '9000000000409', 'Test', 'Water, noedels, zout'),
        ('milk', '9000000000410', 'Test', 'Water, karnemelk, wei, zout'),
        ('milk', '9000000000411', 'Test', 'Vand, sukker, smør, ost, mælk, salt'),
        ('nuts', '9000000000412', 'Test', 'Water, pistachenoten 5%, notenpasta, zout'),
        ('nuts', '9000000000413', 'Test', 'Wasser, Zucker, Cashewkerne 10%, Salz'),
        ('nuts', '9000000000414', 'Test', 'Vatten, hasselnöt 5%, valnöt, salt'),
        ('fish', '9000000000415', 'Test', 'Wasser, Anchovis 10%, Salz'),
        ('fish', '9000000000416', 'Test', 'Vatten, lax, tun, salt'),
        ('crustaceans', '9000000000417', 'Test', 'Vatten, räkor 20%, salt'),
        ('molluscs', '9000000000418', 'Test', 'Water, schelpdieren, zout'),
        ('celery', '9000000000419', 'Test', 'Water, selderie, zout'),
        ('eggs', '9000000000420', 'Test', 'Water, eipoeder, zout'),
        ('milk', '9000000000421', 'Test', 'Water, cacaoboter, suiker'),
        # 3.40 : texte mal lu, allergène collé à du bruit (Joghurt Toffee Mcennedy 20252878)
        ('peanuts', '9000000000430', 'Joghurt Toffee', "tait e sucte caramé!sé, fibres de blé* émue* (scia)' Peut contenir dcs traces de tra ct6arachides. Non ouvett4"),
        ('peanuts', '9000000000431', 'Test', 'sucre, ofpeanut, sel'),
        ('nuts', '9000000000432', 'Test', 'sucre, tait noisettesl, sel'),
        ('crustaceans', '9000000000433', 'Test', 'sucre, deCREVETTE, sel'),
        ('peanuts', '9000000000434', 'Test', 'sucre, acide arachidonique, sel'),
        ('gluten', '9000000000422', 'Test', 'Water, sojabonen, zout'),
    ]
    SAFE = {'9000000000020', '9000000000021', '9000000000022', '9000000000060', '9000000000061', '9000000000062', '9000000000063', '9000000000064',
            '9000000000067', '9000000000068', '9000000000300', '9000000000301', '9000000000302', '9000000000303', '9000000000304', '9000000000305', '9000000000421', '9000000000422', '9000000000434'}
    print('3. Produits réels : jamais « Compatible » quand l\'allergène est écrit sur l\'emballage')
    bad = []
    for sel, code, name, ing in REELS:
        got = verdict([sel], BASE + ing, {'code': code, 'product_name': name})
        want_ok = code in SAFE
        if (got == 'ok') != want_ok: bad.append(f'{code} {sel} / « {name} » / « {ing[:60]} » : {got}')
    check(not bad, f'{len(REELS)} produits ou textes réels' + ('' if not bad else ' :\n    ' + '\n    '.join(bad)))
    print('4. Texte d\'ingrédients illisible (3.37) : « À vérifier », jamais « Compatible »')
    def st(name, ing, sel=('milk', 'gluten', 'eggs', 'nuts')):
        return page.evaluate("""([sel, name, ing]) => { const R = window.__RS; R.profile.sel = new Set(sel); R.profile.words = []; R.profile.traces = false;
          return R.evaluate({ code:'9100000000001', product_name:name, brands:'Favorina', ingredients_text:ing, allergens_tags:[], traces_tags:[], categories_tags:['en:chocolates'] }).status; }""", [list(sel), name, ing])
    LAPIN = ('FAIRKACE icutaurs de vendre davatage de Nconditions Fairtrade, Ensavoir suww,info,fairtrade,net/program, oeUSutritionnelles movemes '
             'Crergle atières grasses ont acides gras saturés ucides nt succes pour 100g 2307 kJ/')
    bad = []
    for name, ing in [('Lapin chocolat', LAPIN),
                      ('Chocolat', 'Valeurs nutritionnelles moyennes pour 100 g : énergie 2307 kJ / 547 kcal, matières grasses 31,9 g dont acides gras saturés 20 g'),
                      ('Chocolat', 'dont acides gras saturés 20 g, protéines 6 g, fibres 3 g'),
                      ('Chocolat', 'Nutrition facts per 100 g energy 2307 kJ fat 31 g'),
                      ('Chocolat', 'graisses protéines fibres vitamines')]:
        got = st(name, ing)
        if got == 'ok': bad.append(f'{name} / « {ing[:50]} » : {got}')
    check(not bad, 'tableau nutritionnel ou texte mal lu : jamais « Compatible »' + ('' if not bad else ' :\n    ' + '\n    '.join(bad)))
    real = [('Chocolat noir', 'pâte de cacao, sucre, beurre de cacao, vanille'), ('Biscuit', 'sucre, huile de palme, sel, arôme naturel'),
            ('Eau aromatisée', 'eau, arôme naturel de citron, acide citrique'),
            ('Bonbons', 'sirop de glucose, sucre, acidifiant : acide citrique, arômes, colorants'),
            ('Dark chocolate', 'cocoa mass, sugar, cocoa butter, vanilla extract'), ('Jam', 'strawberries, sugar, water, pectin, citric acid'),
            ('Purée', 'pommes de terre, sel'), ('Compote', 'pommes, fruits, jus de citron')]
    bad = [f'{n} / « {i} » : {st(n, i, ("peanuts", "fish"))}' for n, i in real if st(n, i, ('peanuts', 'fish')) != 'ok']
    check(not bad, f'{len(real)} textes d\'ingrédients normaux restent « Compatible »' + ('' if not bad else ' :\n    ' + '\n    '.join(bad)))
    check(not errs, 'aucune erreur JavaScript' + (': ' + '; '.join(errs[:3]) if errs else ''))
    b.close()
httpd.shutdown()
print('\n' + ('TOUT EST OK' if not FAIL else f'{len(FAIL)} ÉCHEC(S)'))
sys.exit(1 if FAIL else 0)
