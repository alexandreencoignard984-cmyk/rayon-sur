#!/usr/bin/env python3
"""Sonde des liens « Stock au drive » sur les vrais sites des enseignes.

Lancée par la tâche GitHub « Sonde drive » (les serveurs de GitHub ont accès à internet, pas l'atelier de
Claude). Pour chaque enseigne, prend les produits les plus consultés de la base vus dans cette enseigne, ouvre
la recherche que l'appli propose (et quelques variantes) dans Chromium avec l'allure d'un iPhone, et note :
page bloquée ou non, adresse finale (redirection vers une catégorie ?), produits affichés, code-barres retrouvé.

Écrit sonde/rapport.md et une capture par lien dans sonde/ (publiés sur une branche à part, pas sur main).
Quelques dizaines de pages en tout, une à la fois : rien qui ressemble à une aspiration du site.
Usage : python3 tools/sonde_drive.py [nombre de produits par enseigne, 5 par défaut]
        python3 tools/sonde_drive.py --urls "URL1 URL2 …"   (ouvre seulement ces adresses : pour tester un format de lien)
"""
import datetime, json, os, re, sys, threading, time, unicodedata
from functools import partial
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from playwright.sync_api import sync_playwright

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'sonde')
N = int(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1].isdigit() else 5
CHAINS = ['carrefour', 'leclerc', 'auchan', 'u', 'intermarche', 'monoprix', 'biocoop', 'lidl', 'picard']
# variantes essayées en plus du lien de l'appli : « ean » recherche par code-barres, « nom » marque + nom
EXTRA = {
    'carrefour': [('nom', None), ('fiche', 'https://www.carrefour.fr/p/{ean}')],
    'leclerc': [('nom', None)],
    'auchan': [('ean', 'https://www.auchan.fr/recherche?text={ean}')],
    'u': [('ean', 'https://www.coursesu.com/recherche?q={ean}')],
    'intermarche': [('site-nom', 'https://www.intermarche.com/recherche/{terms}'), ('site-ean', 'https://www.intermarche.com/recherche/{ean}')],
    'monoprix': [('ean', 'https://courses.monoprix.fr/search?q={ean}')],
    'biocoop': [('ean', 'https://www.biocoop.fr/catalogsearch/result/?q={ean}')],
    'lidl': [],
    'picard': [('ean', 'https://www.picard.fr/recherche?q={ean}')],
}
# liens vers une fiche produit, selon les sites
PRODUCT_HREF = re.compile(r'/p/|/fp/|/pr-C|/produit|/product|/products/|-p-\d|/\d{8,14}(\D|$)', re.I)
BLOCK = re.compile(r'captcha|just a moment|attention required|access denied|accès refusé|vérification de sécurité|'
                   r'are you a robot|êtes-vous un robot|pardon our interruption|request unsuccessful|forbidden', re.I)


class Quiet(SimpleHTTPRequestHandler):
    def log_message(self, *a):
        pass


def fold(s):
    return ''.join(c for c in unicodedata.normalize('NFD', str(s).lower()) if unicodedata.category(c) != 'Mn')


PICK = r"""async ([chains, n]) => {
  const R = window.__RS; const idx = await R.loadIndex();
  const seen = new Set(), all = [];
  for (const [tag, a] of Object.entries(idx.aisles)){
    for (let i = 0; i < a.pages; i++){
      const url = 'data/a/' + a.slug + (i ? '.' + (i + 1) : '') + '.json';
      const j = await fetch(url).then(r => r.ok ? r.json() : null).catch(() => null);
      if (!j || !Array.isArray(j.rows)) continue;
      for (const row of j.rows){
        const p = R.fromRow(row); if (seen.has(p.code) || !p.product_name || !p.brands || !/^\d{13}$/.test(p.code)) continue;
        seen.add(p.code); p._aisle = tag; all.push(p);
      }
    }
  }
  all.sort((a, b) => (b.unique_scans_n || 0) - (a.unique_scans_n || 0));
  const out = {};
  for (const id of chains){
    const st = R.STORES.find(s => s.id === id), brands = new Set(), aisles = new Set(), list = [];
    for (const p of all){
      if (!st || !(p.stores_tags || []).some(t => st.tags.includes(t))) continue;
      const b = R.driveBrand(p).toLowerCase();
      if (brands.has(b) || aisles.has(p._aisle)) continue;   // des marques et des rayons différents
      brands.add(b); aisles.add(p._aisle);
      list.push({ code:p.code, name:p.product_name, brand:p.brands, qty:p.quantity, aisle:p._aisle,
        terms:R.driveTerms(p), brandTerm:R.driveBrand(p), app:R.driveUrl(p, id), mode:R.driveMode(p, id), nom:R.driveUrl(p, id, 'nom') });
      if (list.length >= n) break;
    }
    out[id] = list;
  }
  return out;
}"""

READ = r"""() => {
  const txt = document.body ? document.body.innerText : '';
  const links = [...document.querySelectorAll('a[href]')].map(a => ({ h:a.href, t:(a.innerText || a.getAttribute('aria-label') || a.title || '').replace(/\s+/g, ' ').trim() }));
  const h1 = document.querySelector('h1');
  return { title:document.title, h1:h1 ? h1.innerText.trim().slice(0, 120) : '', text:txt.slice(0, 30000), links,
    iframes:[...document.querySelectorAll('iframe')].map(f => f.src).filter(Boolean).slice(0, 10) };
}"""


def probe(ctx, url, shot):
    page = ctx.new_page()
    status, err = None, ''
    try:
        r = page.goto(url, wait_until='domcontentloaded', timeout=45000)
        status = r.status if r else None
        try:
            page.wait_for_load_state('networkidle', timeout=12000)
        except Exception:
            pass
        page.wait_for_timeout(2500)
        for sel in ['#onetrust-accept-btn-handler', 'button:has-text("Tout accepter")', 'button:has-text("Accepter")', 'button:has-text("J\'accepte")']:
            try:
                b = page.locator(sel).first
                if b.is_visible(timeout=500):
                    b.click(timeout=2000); page.wait_for_timeout(1500); break
            except Exception:
                pass
        info = page.evaluate(READ)
        page.screenshot(path=shot, type='jpeg', quality=45)
        final = page.url
    except Exception as e:
        info, final, err = {'title': '', 'h1': '', 'text': '', 'links': [], 'iframes': []}, page.url, str(e).split('\n')[0][:160]
    page.close()
    return status, final, info, err


def judge(item, status, final, info):
    blob = info['title'] + ' ' + info['text'][:1500] + ' ' + ' '.join(info['iframes'])
    blocked = bool(status in (403, 429, 503) or BLOCK.search(blob) or any('captcha' in f for f in info['iframes']))
    prods, seen = [], set()
    for l in info['links']:
        if PRODUCT_HREF.search(l['h']) and l['t'] and len(l['t']) > 6 and l['h'] not in seen:
            seen.add(l['h']); prods.append(l)
    ean_link = next((l for l in prods if item['code'] in l['h']), None)
    bw = [w for w in re.split(r'[^a-z0-9]+', fold(item['brandTerm'])) if len(w) > 2]
    brand_hits = sum(1 for l in prods[:6] if bw and any(w in fold(l['t']) for w in bw))
    return blocked, prods, ean_link, brand_hits


def main():
    os.makedirs(OUT, exist_ok=True)
    srv = ThreadingHTTPServer(('127.0.0.1', 0), partial(Quiet, directory=ROOT))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    base = f'http://127.0.0.1:{srv.server_address[1]}/'
    rows, lines = [], []
    with sync_playwright() as p:
        b = p.chromium.launch()
        app = b.new_context()
        app.add_init_script("localStorage.setItem('rs2:profile', JSON.stringify({sel:[], traces:false, words:[]})); localStorage.setItem('rs2:geoAsked', '1');")
        app.route(lambda u: not u.startswith(base), lambda r: r.abort())
        page = app.new_page(); page.goto(base)
        page.wait_for_function('() => window.__RS && window.__RS.STORES', timeout=30000)
        picks = page.evaluate(PICK, [CHAINS, N])
        version = page.evaluate("() => document.querySelector('#appVersion').textContent")
        app.close()

        iphone = dict(p.devices['iPhone 13'])
        iphone.pop('default_browser_type', None)
        ctx = b.new_context(**iphone, locale='fr-FR', timezone_id='Europe/Paris')
        k = 0
        for chain in CHAINS:
            for item in picks.get(chain, []):
                variants = [('appli:' + item['mode'], item['app'])]
                for name, tpl in EXTRA.get(chain, []):
                    url = item['nom'] if tpl is None else tpl.format(ean=item['code'], terms=item['terms'].replace(' ', '%20'))
                    if url not in [v[1] for v in variants]:
                        variants.append((name, url))
                for vname, url in variants:
                    k += 1
                    shot = os.path.join(OUT, f'{k:03d}-{chain}-{re.sub(r"[^a-z]", "", vname)}.jpg')
                    status, final, info, err = probe(ctx, url, shot)
                    blocked, prods, ean_link, brand_hits = judge(item, status, final, info)
                    rows.append(dict(chain=chain, item=item, variant=vname, url=url, status=status, final=final, blocked=blocked,
                                     n=len(prods), ean=bool(ean_link), brand_hits=brand_hits, first=[l['t'][:70] for l in prods[:4]],
                                     title=info['title'][:90], h1=info['h1'], err=err, shot=os.path.basename(shot)))
                    print(f"{k:3d} {chain:11s} {vname:14s} {status} bloqué={blocked} produits={len(prods)} ean={bool(ean_link)} marque={brand_hits} {final[:90]}", flush=True)
                    time.sleep(2)
        b.close()
    srv.shutdown()

    json.dump(rows, open(os.path.join(OUT, 'resultats.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    lines = ['# Sonde des liens drive', '',
             f'Sonde du {datetime.datetime.now(datetime.timezone.utc).strftime("%d/%m/%Y %H:%M")} UTC, appli {version}, {N} produits par enseigne, '
             'Chromium avec l\'allure d\'un iPhone depuis un serveur GitHub (les sites peuvent bloquer ce type de serveur).', '',
             '| Enseigne | Lien | Pages | Bloquées | Code-barres retrouvé | Marque dans les 1ers résultats | Redirigées |', '|---|---|---:|---:|---:|---:|---:|']
    groups = {}
    for r in rows:
        groups.setdefault((r['chain'], r['variant']), []).append(r)
    for (chain, var), lst in groups.items():
        ok = [r for r in lst if not r['blocked'] and not r['err']]
        moved = sum(1 for r in ok if r['final'].split('?')[0] != r['url'].split('?')[0])
        lines.append(f"| {chain} | {var} | {len(lst)} | {len(lst) - len(ok)} | {sum(r['ean'] for r in ok)} | {sum(1 for r in ok if r['brand_hits'])} | {moved} |")
    lines += ['', '## Détail', '']
    for r in rows:
        it = r['item']
        lines.append(f"- **{r['chain']} · {r['variant']}** · {it['brand']} – {it['name']} ({it['code']}) · `{r['url']}`")
        lines.append(f"  - statut {r['status']}, final `{r['final'][:140]}`, titre « {r['title']} », h1 « {r['h1'][:60]} »"
                     + (' · **bloqué**' if r['blocked'] else '') + (f" · erreur {r['err']}" if r['err'] else ''))
        lines.append(f"  - {r['n']} liens produit, code-barres {'oui' if r['ean'] else 'non'}, marque dans {r['brand_hits']} des 6 premiers : "
                     + ' | '.join(r['first']) + f" · capture {r['shot']}")
    report = '\n'.join(lines) + '\n'
    open(os.path.join(OUT, 'rapport.md'), 'w', encoding='utf-8').write(report)
    if os.environ.get('GITHUB_STEP_SUMMARY'):
        open(os.environ['GITHUB_STEP_SUMMARY'], 'a', encoding='utf-8').write(report)


def urls_only(urls):
    """Ouvre chaque adresse, note statut, adresse finale, titre et début du texte, avec une capture."""
    os.makedirs(OUT, exist_ok=True)
    rows = []
    with sync_playwright() as p:
        b = p.chromium.launch()
        iphone = dict(p.devices['iPhone 13'])
        iphone.pop('default_browser_type', None)
        ctx = b.new_context(**iphone, locale='fr-FR', timezone_id='Europe/Paris')
        for k, url in enumerate(urls, 1):
            shot = os.path.join(OUT, f'u{k:02d}.jpg')
            status, final, info, err = probe(ctx, url, shot)
            text = re.sub(r'\s+', ' ', info['text'])[:1500]
            rows.append(dict(url=url, status=status, final=final, title=info['title'][:120], h1=info['h1'], text=text, err=err,
                             links=[l for l in info['links'] if l['t']][:80], shot=os.path.basename(shot)))
            print(f'{k:2d} {status} {final[:100]} « {info["title"][:60]} » {err}', flush=True)
            time.sleep(3)
        b.close()
    json.dump(rows, open(os.path.join(OUT, 'adresses.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    lines = ['# Sonde : adresses testées', '']
    for r in rows:
        lines += [f"- `{r['url']}`", f"  - statut {r['status']}, final `{r['final'][:160]}`, titre « {r['title']} »" + (f", erreur {r['err']}" if r['err'] else ''),
                  f"  - {r['text'][:400]}", f"  - capture {r['shot']}"]
    open(os.path.join(OUT, 'rapport.md'), 'w', encoding='utf-8').write('\n'.join(lines) + '\n')


if __name__ == '__main__':
    if len(sys.argv) > 2 and sys.argv[1] == '--urls':
        urls_only(sys.argv[2].split())
    else:
        main()
