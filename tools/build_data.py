#!/usr/bin/env python3
"""Construit le dossier data/ de Rayon sûr.

Source : l'export CSV complet d'Open Food Facts (mis à jour chaque jour par Open Food Facts).
On garde les produits vendus en France, rangés par rayon (catégories de tools/config.json),
avec juste les champs dont l'appli a besoin. L'appli lit ensuite ces fichiers sur GitHub Pages :
plus aucune recherche n'est envoyée à Open Food Facts pour parcourir un rayon.

Usage : python3 tools/build_data.py [chemin_du_csv.gz]
"""
import datetime, gzip, json, os, re, subprocess, sys, time, unicodedata

import duckdb

CSV_URL = 'https://static.openfoodfacts.org/data/en.openfoodfacts.org.products.csv.gz'
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CFG = json.load(open(os.path.join(ROOT, 'tools', 'config.json'), encoding='utf-8'))
OUT = os.path.join(ROOT, 'data')
PAGE_ROWS = int(os.environ.get('PAGE_ROWS', 1500))
MAX_PAGES = int(os.environ.get('MAX_PAGES', 4))
IMG_PREFIX = 'https://images.openfoodfacts.org/images/products/'
COLS = ['code', 'name', 'brands', 'qty', 'stores', 'allergens', 'traces', 'labels', 'ingr', 'analysis',
        'nutri', 'nscore', 'nova', 'eco', 'escore', 'img', 'scans', 'nut', 'ai', 'q', 'mod', 'ia']
# q : fiabilité de la liste d'ingrédients — « i » à compléter selon Open Food Facts. (La part d'ingrédients non
#     reconnus n'est pas fiable dans l'export : l'appli la prend dans la fiche en direct.)
# mod : date de dernière modification de la fiche (jour, AAAA-MM-JJ)
# ia : allergènes repérés dans les ingrédients reconnus par Open Food Facts (même s'ils ne sont pas déclarés)
INGR_MAX = 6000
# ingrédients de la taxonomie d'Open Food Facts → allergène (les parents sont inclus dans ingredients_tags)
IA = {
    'en:milk': ['en:milk', 'en:dairy', 'en:cheese', 'en:whey', 'en:lactose', 'en:casein', 'en:yogurt', 'en:milk-powder', 'en:milk-proteins'],
    'en:gluten': ['en:wheat', 'en:barley', 'en:rye', 'en:oat', 'en:spelt', 'en:gluten', 'en:kamut', 'en:durum-wheat', 'en:triticale'],
    'en:eggs': ['en:egg'],
    'en:nuts': ['en:almond', 'en:hazelnut', 'en:walnut', 'en:cashew-nut', 'en:pistachio', 'en:pecan-nut', 'en:macadamia-nut', 'en:brazil-nut'],
    'en:peanuts': ['en:peanut'],
    'en:soybeans': ['en:soya', 'en:soybean'],
    'en:sesame-seeds': ['en:sesame', 'en:sesame-seed'],
    'en:fish': ['en:fish'],
    'en:crustaceans': ['en:crustacean', 'en:shrimp', 'en:prawn', 'en:crab', 'en:lobster'],
    'en:molluscs': ['en:mollusc', 'en:mussel', 'en:oyster', 'en:squid', 'en:octopus', 'en:scallop', 'en:clam', 'en:snail'],
    'en:celery': ['en:celery'], 'en:mustard': ['en:mustard'], 'en:lupin': ['en:lupin'],
    'en:sulphur-dioxide-and-sulphites': ['en:sulphur-dioxide', 'en:e220', 'en:e221', 'en:e222', 'en:e223', 'en:e224', 'en:e226', 'en:e227', 'en:e228'],
}
IA_OF = {t: a for a, ts in IA.items() for t in ts}


def ingredient_info(tags_text, states_text):
    """(q, ia) à partir de ingredients_tags et states_tags."""
    tags = [t.strip() for t in (tags_text or '').split(',') if t.strip()]
    q = ''
    if 'en:ingredients-to-be-completed' in (states_text or ''):
        q += 'i'
    ia = sorted({IA_OF[t] for t in tags if t in IA_OF})
    return q, ','.join(ia)
NUT = ['energy-kcal_100g', 'fat_100g', 'saturated-fat_100g', 'carbohydrates_100g', 'sugars_100g', 'fiber_100g', 'proteins_100g', 'salt_100g']
LABELS_KEEP = {'en:no-lactose', 'en:no-gluten', 'en:no-milk', 'en:vegan', 'en:vegetarian', 'en:organic', 'en:eu-organic',
               'fr:ab-agriculture-biologique', 'en:palm-oil-free', 'en:no-palm-oil', 'en:no-added-sugar', 'en:no-eggs',
               'en:fair-trade', 'en:made-in-france', 'en:no-preservatives', 'en:no-colorings', 'en:no-artificial-flavors', 'fr:label-rouge'}
LACTOSE_LABEL = re.compile(r'(no-lactose|lactose-free|sans-lactose)')
ANALYSIS_KEEP = {'en:vegan', 'en:vegetarian', 'en:palm-oil-free', 'en:non-vegan', 'en:non-vegetarian', 'en:palm-oil'}
T0 = time.time()


def log(*a):
    print(f'[{time.time() - T0:6.1f}s]', *a, flush=True)


def fold(s):
    s = unicodedata.normalize('NFKD', s or '').encode('ascii', 'ignore').decode().lower()
    return re.sub(r'\s+', ' ', re.sub(r"[^a-z0-9+&]+", ' ', s)).strip()


# rayons affichés dans l'appli, puis catégories utilisées par les recettes (une seule page chacune)
AISLES = [a['tag'] for a in CFG['aisles']] + [a['tag'] for a in CFG.get('extra', [])]
PAGES_OF = {a['tag']: a.get('pages', MAX_PAGES) for a in CFG['aisles'] + CFG.get('extra', [])}
AISLE_IDX = {t: i for i, t in enumerate(AISLES)}
STORES = []
for s in CFG['stores']:
    flags = re.I if 'i' in (s.get('flags') or '') else 0
    STORES.append((s['id'], re.compile(s['match'], flags) if s.get('match') else None, [fold(m) for m in s.get('mdd', [])]))


def chains_of(stores_text):
    if not stores_text:
        return []
    return [sid for sid, rx, _ in STORES if rx and rx.search(stores_text)]


def is_mdd(brands):
    bl = [fold(b) for b in (brands or '').split(',') if b.strip()]
    for _, _, mdd in STORES:
        for b in bl:
            for m in mdd:
                if m and (b == m or b.startswith(m + ' ')):
                    return True
    return False


def num(v, nd=2):
    if v is None or v == '':
        return None
    try:
        f = float(v)
    except ValueError:
        return None
    if f != f or abs(f) > 1e6:
        return None
    r = round(f, nd)
    return int(r) if r == int(r) else r


def clean_list(v, keep=None, rx=None):
    out = []
    for t in (v or '').split(','):
        t = t.strip()
        if t and (keep is None or t in keep or (rx and rx.search(t))):
            out.append(t)
    return ','.join(dict.fromkeys(out))


def download(path):
    if os.path.exists(path) and os.path.getsize(path) > 100e6:
        log('csv déjà présent', path)
    else:
        log('téléchargement', CSV_URL)
        subprocess.run(['curl', '-sSL', '--retry', '5', '--retry-delay', '20', '-A', 'RayonSur/1.0 (github.com/alexandreencoignard984-cmyk/rayon-sur)', '-o', path, CSV_URL], check=True)
    head = subprocess.run(['curl', '-sSIL', CSV_URL], capture_output=True, text=True).stdout
    found = re.findall(r'(?im)^last-modified:\s*(.+?)\s*$', head)
    return found[-1] if found else ''


def main():
    src = sys.argv[1] if len(sys.argv) > 1 else '/tmp/off-products.csv.gz'
    export_date = '' if os.environ.get('NO_DOWNLOAD') else download(src)
    log('taille', os.path.getsize(src))
    con = duckdb.connect()
    con.execute("SET preserve_insertion_order=false")
    # Le serveur GitHub a ~16 Go : peu de fils, et fichiers temporaires sur disque plutôt que tout en mémoire
    con.execute("SET threads=2")
    con.execute("SET temp_directory='/tmp/duckdb-tmp'")
    pattern = ',(' + '|'.join(re.escape(t) for t in AISLES) + '),'
    nut_sql = ', '.join(f'"{c}"' for c in NUT)
    # colonnes facultatives : prises si l'export les contient (sinon vides, sans faire échouer la construction)
    with gzip.open(src, 'rt', encoding='utf-8', errors='replace') as fh:
        header = set(fh.readline().rstrip('\n').split('\t'))
    opt = lambda c: f'"{c}"' if c in header else f'NULL AS "{c}"'
    log('colonnes facultatives :', {c: c in header for c in ('ingredients_tags', 'states_tags', 'last_modified_t')})
    q = f"""
      SELECT code, product_name, brands, quantity, stores, categories_tags, labels_tags, allergens, traces_tags,
             ingredients_text, ingredients_analysis_tags, nutriscore_grade, nutriscore_score, nova_group,
             environmental_score_grade, environmental_score_score, image_small_url, unique_scans_n, {nut_sql},
             {opt('ingredients_tags')}, {opt('states_tags')}, {opt('last_modified_t')}
      FROM read_csv('{src}', delim='\t', quote='', escape='', header=true, all_varchar=true, ignore_errors=true,
                    max_line_size=20000000, parallel=false)
      WHERE countries_tags LIKE '%en:france%'
        AND product_name IS NOT NULL AND product_name <> ''
        AND regexp_matches(',' || coalesce(categories_tags, '') || ',', '{pattern}')
    """
    # lecture par paquets : fetchall() gardait deux copies de ~500 000 lignes (DuckDB + Python) et manquait de mémoire
    cur = con.execute(q)
    rows = []
    while True:
        chunk = cur.fetchmany(20000)
        if not chunk:
            break
        rows.extend(chunk)
    log('produits France dans nos rayons :', len(rows))

    by_aisle = {t: [] for t in AISLES}
    seen = set()
    kept_codes = 0
    for r in rows:
        (code, name, brands, qty, stores, cats, labels, allergens, traces, ingr, analysis, nutri, nscore, nova,
         eco, escore, img, scans) = r[:18]
        nuts = r[18:18 + len(NUT)]
        itags, states, modt = r[18 + len(NUT):]
        code = (code or '').strip()
        if not code.isdigit() or code in seen:
            continue
        seen.add(code)
        ai = sorted({AISLE_IDX[c] for c in (cats or '').split(',') if c in AISLE_IDX})
        if not ai:
            continue
        ingr = (ingr or '').strip()
        if len(ingr) > INGR_MAX:
            ingr = ingr[:INGR_MAX]
        q, ia = ingredient_info(itags, states)
        try:
            mod = datetime.datetime.fromtimestamp(int(modt), datetime.timezone.utc).strftime('%Y-%m-%d') if modt else ''
        except (ValueError, OverflowError, OSError):
            mod = ''
        allergens = clean_list(allergens)
        chains = chains_of(stores)
        has_info = bool(ingr) or bool(allergens)
        sc = int(num(scans, 0) or 0)
        mdd = is_mdd(brands)
        if not (has_info or chains or mdd or sc >= 3):
            continue
        if img and img.startswith(IMG_PREFIX) and img.endswith('.200.jpg'):
            img = img[len(IMG_PREFIX):-len('.200.jpg')]
        nut = [num(v) for v in nuts]
        row = [
            code, name.strip()[:200], (brands or '').strip()[:120], (qty or '').strip()[:40], ','.join(chains),
            allergens, clean_list(traces), clean_list(labels, LABELS_KEEP, LACTOSE_LABEL), ingr,
            clean_list(analysis, ANALYSIS_KEEP),
            nutri if nutri in ('a', 'b', 'c', 'd', 'e') else '', num(nscore, 0),
            num(nova, 0) if (nova or '') in ('1', '2', '3', '4') else None,
            eco if eco in ('a-plus', 'a', 'b', 'c', 'd', 'e', 'f') else '', num(escore, 0),
            img or '', sc, nut if any(v is not None for v in nut) else None, ai, q, mod, ia,
        ]
        kept_codes += 1
        rank = (2 if has_info else 0) + (1 if (chains or mdd) else 0)
        for i in ai:
            by_aisle[AISLES[i]].append((rank, sc, code, row))
    del rows
    log('produits retenus :', kept_codes)
    # export tronqué ou format changé chez Open Food Facts : on garde la base de la semaine précédente
    min_products = int(os.environ.get('MIN_PRODUCTS', 100000))
    if kept_codes < min_products:
        log(f'ARRÊT : {kept_codes} produits seulement (minimum {min_products}), la base existante est conservée.')
        sys.exit(1)

    os.makedirs(os.path.join(OUT, 'a'), exist_ok=True)
    written = set()
    index = {}
    total_bytes = 0
    for tag in AISLES:
        items = by_aisle[tag]
        items.sort(key=lambda x: (-x[0], -x[1], x[2]))
        kept = items[:PAGE_ROWS * PAGES_OF.get(tag, MAX_PAGES)]
        pages = [kept[i:i + PAGE_ROWS] for i in range(0, len(kept), PAGE_ROWS)] or [[]]
        slug = tag.replace(':', '-')
        for pi, page in enumerate(pages, 1):
            page = sorted(page, key=lambda x: x[2])
            fn = f'{slug}.json' if pi == 1 else f'{slug}.{pi}.json'
            body = '{"tag":%s,"page":%d,"pages":%d,"rows":[\n%s\n]}\n' % (
                json.dumps(tag), pi, len(pages),
                ',\n'.join(json.dumps(x[3], ensure_ascii=False, separators=(',', ':')) for x in page))
            path = os.path.join(OUT, 'a', fn)
            with open(path, 'w', encoding='utf-8') as f:
                f.write(body)
            written.add(fn)
            total_bytes += len(body.encode())
        index[tag] = {'slug': slug, 'n': len(kept), 'pages': len(pages), 'total': len(items)}
        log(f'  {tag}: {len(kept)}/{len(items)} produits, {len(pages)} page(s)')
    for fn in os.listdir(os.path.join(OUT, 'a')):
        if fn not in written:
            os.remove(os.path.join(OUT, 'a', fn))
    built = datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat().replace('+00:00', 'Z')
    idx = {'v': 1, 'built': built, 'export': export_date, 'img': IMG_PREFIX, 'cols': COLS, 'nut': NUT,
           'order': AISLES, 'products': kept_codes, 'aisles': index}
    with open(os.path.join(OUT, 'index.json'), 'w', encoding='utf-8') as f:
        json.dump(idx, f, ensure_ascii=False, separators=(',', ':'))
    log(f'terminé : {len(written)} fichiers, {total_bytes / 1e6:.1f} Mo')


if __name__ == '__main__':
    main()
