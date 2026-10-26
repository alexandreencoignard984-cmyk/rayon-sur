"""Lecture de l'export Open Food Facts (tools/build_data.py › read_rows), hors réseau : un mini CSV.gz avec une ligne
mal formée, une ligne sans en:france, un produit sans nom, un autre hors de nos rayons. Si DuckDB est installé,
le résultat est aussi comparé à l'ancienne requête DuckDB (celle qui manquait de mémoire).
Usage : python3 tests/base_produits.py"""
import gzip, os, re, sys, tempfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'tools'))
import build_data as B

FAIL = []
def check(ok, msg):
    print(('  ok ' if ok else '  ÉCHEC ') + msg)
    if not ok: FAIL.append(msg)

HEAD = ['code', 'product_name', 'brands', 'quantity', 'stores', 'categories_tags', 'labels_tags', 'allergens', 'traces_tags',
        'ingredients_text', 'ingredients_analysis_tags', 'nutriscore_grade', 'nutriscore_score', 'nova_group',
        'environmental_score_grade', 'environmental_score_score', 'image_small_url', 'unique_scans_n'] + B.NUT + \
       ['ingredients_tags', 'states_tags', 'last_modified_t', 'countries_tags', 'colonne_inutile']
TAG = B.AISLES[0]
def line(**kw):
    d = {c: '' for c in HEAD}; d.update(kw)
    return '\t'.join(d[c] for c in HEAD)
LINES = [
    line(code='1', product_name='Biscuit "beurre" é', brands='Marque', categories_tags='en:snacks,' + TAG, countries_tags='en:belgium,en:france',
         ingredients_text="farine, sucre, l'œuf", **{'energy-kcal_100g': '450', 'salt_100g': '0.5'}, last_modified_t='1700000000'),   # gardé
    line(code='2', product_name='Vendu ailleurs', categories_tags=TAG, countries_tags='en:germany'),                                       # pas en:france
    line(code='3', product_name='', categories_tags=TAG, countries_tags='en:france'),                                                     # sans nom
    line(code='4', product_name='Hors rayon', categories_tags='en:zzz-inconnu', countries_tags='en:france'),                              # autre rayon
    line(code='5', product_name='Rayon collé', categories_tags='en:x' + TAG + ',en:y', countries_tags='en:france'),                   # étiquette qui contient le rayon sans l'être
    line(code='6', product_name='Mal formé', categories_tags=TAG, countries_tags='en:france') + '\textra',                           # trop de colonnes
    '7\ttronqué en:france',                                                                                                           # trop peu de colonnes
    line(code='8', product_name='Deuxième', categories_tags=TAG + ',en:snacks', countries_tags='en:france', allergens='en:milk'),     # gardé
    line(code='9', product_name='Pays voisin', categories_tags=TAG, countries_tags='en:france-metropolitaine'),                           # contient « en:france » : gardé comme l'ancienne requête (LIKE)
]
tmp = tempfile.mkdtemp()
src = os.path.join(tmp, 'mini.csv.gz')
with gzip.open(src, 'wb') as f:
    f.write(('\t'.join(HEAD) + '\n' + '\n'.join(LINES) + '\n').encode('utf-8'))

print('Lecture en flux de l\'export')
rows = B.read_rows(src)
codes = [r[0] for r in rows]
check(codes == ['1', '8', '9'], f'produits gardés, dans l\'ordre du fichier : {codes}')
r1 = rows[0]
check(r1[1] == 'Biscuit "beurre" é' and r1[9] == "farine, sucre, l'œuf", 'guillemets et accents conservés tels quels')
check(r1[2] == 'Marque' and r1[3] is None and r1[4] is None and r1[7] is None, "champs vides rendus None")
check(len(r1) == 18 + len(B.NUT) + 3, f'même nombre de colonnes que l\'ancienne requête ({len(r1)})')
check(r1[18 + B.NUT.index('energy-kcal_100g')] == '450' and r1[-1] == '1700000000', 'nutriments et date à la bonne place')
check(rows[1][7] == 'en:milk', 'allergènes lus')

# sans les colonnes facultatives : None, sans échec
head2 = [c for c in HEAD if c not in ('ingredients_tags', 'states_tags', 'last_modified_t')]
src2 = os.path.join(tmp, 'mini2.csv.gz')
with gzip.open(src2, 'wb') as f:
    f.write(('\t'.join(head2) + '\n' + '\t'.join({'code': '1', 'product_name': 'A', 'categories_tags': TAG, 'countries_tags': 'en:france'}.get(c, '') for c in head2) + '\n').encode())
r = B.read_rows(src2)
check(len(r) == 1 and r[0][-3:] == (None, None, None), 'colonnes facultatives absentes : None')

try:
    import duckdb
except ImportError:
    duckdb = None
if duckdb:
    print('Comparaison avec l\'ancienne requête DuckDB')
    pattern = ',(' + '|'.join(re.escape(t) for t in B.AISLES) + '),'
    nut_sql = ', '.join(f'"{c}"' for c in B.NUT)
    q = f"""SELECT code, product_name, brands, quantity, stores, categories_tags, labels_tags, allergens, traces_tags,
      ingredients_text, ingredients_analysis_tags, nutriscore_grade, nutriscore_score, nova_group,
      environmental_score_grade, environmental_score_score, image_small_url, unique_scans_n, {nut_sql},
      "ingredients_tags", "states_tags", "last_modified_t"
      FROM read_csv('{src}', delim='\\t', quote='', escape='', header=true, all_varchar=true, ignore_errors=true, max_line_size=20000000, parallel=false)
      WHERE countries_tags LIKE '%en:france%' AND product_name IS NOT NULL AND product_name <> ''
        AND regexp_matches(',' || coalesce(categories_tags, '') || ',', '{pattern}')"""
    old = [tuple(x) for x in duckdb.connect().execute(q).fetchall()]
    check(old == [tuple(x) for x in rows], f'même résultat que DuckDB ({len(old)} produits)')
else:
    print('  (DuckDB absent : comparaison faite avec les résultats attendus à la main)')

print('\n' + ('TOUT EST OK' if not FAIL else f'{len(FAIL)} ÉCHEC(S)'))
sys.exit(1 if FAIL else 0)
