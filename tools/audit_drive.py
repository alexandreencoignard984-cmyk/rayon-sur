#!/usr/bin/env python3
"""Contrôle des recherches « Stock au drive » sur toute la base de l'appli.

Pour chaque produit de data/, calcule la recherche que l'appli enverrait aux sites des enseignes,
avec le code de l'appli elle-même (index.html ouvert dans Chromium), puis signale les cas suspects :
recherche d'un seul mot, sans marque, avec des chiffres, des mots anglais, trop longue.
Les sites des enseignes ne sont pas interrogés (ils bloquent les robots) : on contrôle notre côté.

Écrit rapports/recherches-drive.md (et le résumé de la tâche GitHub si elle tourne là-bas).
Échoue si une catégorie grave dépasse son seuil : une modification a dégradé les recherches.
Usage : python3 tools/audit_drive.py
"""
import datetime, json, os, sys, threading
from functools import partial
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from playwright.sync_api import sync_playwright

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'rapports', 'recherches-drive.md')
# part maximale tolérée (en %) des produits les plus consultés ; au-delà, la tâche échoue
LIMITS = {'vide': 0.5, 'un_mot': 5, 'chiffres': 2, 'anglais': 10, 'long': 2}
LABELS = {
    'vide': 'Recherche vide',
    'un_mot': 'Un seul mot alors que le nom en dit plus',
    'sans_marque': 'Sans marque (recherche sur le nom seul)',
    'chiffres': 'Chiffres hors de la marque',
    'anglais': 'Contient un mot anglais',
    'long': 'Plus de 45 caractères',
}
# mots anglais fréquents sur les fiches, absents du français courant
EN = ['chocolate', 'cheese', 'milk', 'cream', 'strawberry', 'raspberry', 'vanilla', 'butter', 'peanut', 'coconut', 'almond', 'oat',
      'oats', 'wheat', 'bread', 'salted', 'smoked', 'chicken', 'beef', 'pork', 'tuna', 'sugar', 'honey', 'apple', 'lemon', 'nut', 'nuts',
      'crispy', 'spicy', 'protein', 'dark', 'white', 'black', 'red', 'green', 'whole', 'fresh', 'sweet', 'flavoured', 'drink', 'juice',
      'water', 'rice', 'tomato', 'garlic', 'onion', 'pepper', 'yogurt', 'yoghurt', 'dairy', 'style', 'natural', 'greek', 'plain', 'with',
      'and', 'of']   # pas « chips », « cookie », « vegan », « mix »… employés en français


class Quiet(SimpleHTTPRequestHandler):
    def log_message(self, *a):
        pass


JS = r"""async (EN) => {
  const R = window.__RS; const idx = await R.loadIndex();
  const en = new Set(EN), seen = new Set(), rows = [];
  for (const [tag, a] of Object.entries(idx.aisles)){
    for (let i = 0; i < a.pages; i++){
      const url = 'data/a/' + a.slug + (i ? '.' + (i + 1) : '') + '.json';
      const j = await fetch(url).then(r => r.ok ? r.json() : null).catch(() => null);
      if (!j || !Array.isArray(j.rows)) continue;
      for (const row of j.rows){
        const p = R.fromRow(row); if (seen.has(p.code) || !p.product_name) continue;
        seen.add(p.code);
        const t = R.driveTerms(p), brand = R.driveBrand(p);
        const words = t.split(/\s+/).filter(Boolean);
        const low = t.toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, '');
        const f = [];
        if (!t.trim()) f.push('vide');
        const fold = x => String(x).toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, '');
        const bw = new Set(fold(brand).split(/[^a-z0-9]+/));
        // le nom contient-il d'autres mots utiles que la marque ?
        const extra = fold(p.product_name).split(/[^a-z]+/).filter(w => w.length > 2 && !bw.has(w) && !en.has(w) && !['les', 'des', 'aux', 'avec', 'sans', 'pour', 'the', 'original', 'classic', 'classique'].includes(w));
        if (words.length <= 1 && extra.length >= (brand ? 1 : 2)) f.push('un_mot');
        if (!brand) f.push('sans_marque');
        if (/\d/.test(brand ? t.slice(brand.length) : t)) f.push('chiffres');
        const tw = low.split(/[^a-z]+/).filter(Boolean);
        if (tw.some(w => en.has(w) && !bw.has(w))) f.push('anglais');
        if (t.length > 45) f.push('long');
        rows.push([p.code, p.product_name, brand, t, p.unique_scans_n || 0, f]);
      }
    }
  }
  return rows;
}"""


def main():
    port_srv = ThreadingHTTPServer(('127.0.0.1', 0), partial(Quiet, directory=ROOT))
    threading.Thread(target=port_srv.serve_forever, daemon=True).start()
    base = f'http://127.0.0.1:{port_srv.server_address[1]}/'
    with sync_playwright() as p:
        b = p.chromium.launch()
        ctx = b.new_context()
        ctx.add_init_script("localStorage.setItem('rs2:profile', JSON.stringify({sel:[], traces:false, words:[]})); localStorage.setItem('rs2:geoAsked', '1');")
        ctx.route(lambda u: not u.startswith(base), lambda r: r.abort())   # rien vers internet
        page = ctx.new_page()
        page.goto(base)
        page.wait_for_function('() => window.__RS && window.__RS.driveTerms', timeout=30000)
        rows = page.evaluate(JS, EN)
        version = page.evaluate("() => document.querySelector('#appVersion').textContent")
        b.close()
    port_srv.shutdown()

    n = len(rows)
    top = sorted(rows, key=lambda r: -r[4])[:max(1, n // 10)]   # les 10 % les plus consultés
    def share(lst, k):
        return 100 * sum(1 for r in lst if k in r[5]) / max(1, len(lst))
    clean = 100 * sum(1 for r in rows if not (set(r[5]) - {'sans_marque'})) / max(1, n)
    lines = [f'# Recherches « Stock au drive »', '',
             f'Contrôle du {datetime.date.today().strftime("%d/%m/%Y")}, appli {version}, {n:,} produits'.replace(',', ' ') + '.',
             'Chaque produit reçoit la recherche que l\'appli envoie aux sites des enseignes (marque + 2 mots utiles du nom).',
             'Les sites eux-mêmes ne sont pas interrogés : pour ça, utilise « Tester les liens drive » dans Profil.', '',
             f'**{clean:.1f} %** des recherches sans défaut (hors « sans marque »).', '',
             '| Cas | Toute la base | 10 % les plus consultés | Seuil |', '|---|---:|---:|---:|']
    failed = []
    for k, lab in LABELS.items():
        a, t = share(rows, k), share(top, k)
        lim = LIMITS.get(k)
        bad = lim is not None and t > lim
        if bad:
            failed.append(f'{lab} : {t:.1f} % (seuil {lim} %)')
        lines.append(f'| {lab} | {a:.1f} % | {t:.1f} % {"⚠️" if bad else ""} | {f"{lim} %" if lim is not None else "—"} |')
    for k, lab in LABELS.items():
        ex = [r for r in sorted(rows, key=lambda r: -r[4]) if k in r[5]][:12]
        if not ex:
            continue
        lines += ['', f'## {lab}', '', '| Produit | Marque | Recherche | Code |', '|---|---|---|---|']
        for r in ex:
            lines.append(f'| {r[1][:60].replace("|", "/")} | {r[2][:30].replace("|", "/")} | « {r[3].replace("|", "/")} » | {r[0]} |')
    report = '\n'.join(lines) + '\n'
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    open(OUT, 'w', encoding='utf-8').write(report)
    if os.environ.get('GITHUB_STEP_SUMMARY'):
        open(os.environ['GITHUB_STEP_SUMMARY'], 'a', encoding='utf-8').write(report)
    print('\n'.join(lines[:16]))
    if failed:
        print('\nSEUIL DÉPASSÉ :\n- ' + '\n- '.join(failed))
        return 1
    print('\nContrôle OK')
    return 0


if __name__ == '__main__':
    sys.exit(main())
