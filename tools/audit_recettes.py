#!/usr/bin/env python3
"""Contrôle des recettes sur la vraie base : chaque ingrédient acheté en magasin doit trouver des produits.

Pour chaque ingrédient utilisé par une recette (hors produits frais et placard), lance la recherche de l'appli
elle-même (pickFor, index.html dans Chromium) avec un profil sans allergie puis avec les allergies les plus
courantes, et signale les ingrédients sans aucun produit. Écrit rapports/recettes.md.
Échoue si un ingrédient ne trouve rien sans allergie : la base ou une catégorie de tools/config.json a changé.
Usage : python3 tools/audit_recettes.py
"""
import datetime, os, sys, threading
from functools import partial
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from playwright.sync_api import sync_playwright

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'rapports', 'recettes.md')
PROFILES = [('sans allergie', []), ('lait', ['milk']), ('gluten', ['gluten']), ('œufs', ['eggs']), ('fruits à coque', ['nuts'])]


class Quiet(SimpleHTTPRequestHandler):
    def log_message(self, *a):
        pass


JS = r"""async (profiles) => {
  const R = window.__RS, st = R.storeById('all');
  const used = new Map();
  for (const r of R.RECIPES) for (const x of r.i){ const ing = R.ING[x[0]]; if (!ing || ing.f || ing.b) continue;
    if (!used.has(x[0])) used.set(x[0], []); used.get(x[0]).push(r.n); }
  const out = [];
  for (const [id, recs] of used){
    const row = { id, n:R.ING[id].n, recs:recs.length, res:{} };
    for (const [lab, sel] of profiles){
      R.testProfile(sel);
      let r; try { r = await R.pickFor(id, st); } catch (e) { r = { status:'erreur' }; }
      row.res[lab] = { status:r.status, n:(r.alts || []).length, name:r.p ? (r.p.product_name || '') + ' · ' + (r.p.brands || '').split(',')[0] : '' };
    }
    out.push(row);
  }
  return out;
}"""


def main():
    srv = ThreadingHTTPServer(('127.0.0.1', 0), partial(Quiet, directory=ROOT))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    base = f'http://127.0.0.1:{srv.server_address[1]}/'
    with sync_playwright() as p:
        b = p.chromium.launch()
        ctx = b.new_context()
        ctx.add_init_script("localStorage.setItem('rs2:profile', JSON.stringify({sel:[], traces:false, words:[]})); localStorage.setItem('rs2:geoAsked', '1');")
        ctx.route(lambda u: not u.startswith(base), lambda r: r.abort())
        page = ctx.new_page(); page.goto(base)
        page.wait_for_function('() => window.__RS && window.__RS.pickFor', timeout=30000)
        page.set_default_timeout(0)
        rows = page.evaluate(JS, PROFILES)
        version = page.evaluate("() => document.querySelector('#appVersion').textContent")
        b.close()
    srv.shutdown()

    rows.sort(key=lambda r: (r['res']['sans allergie']['status'] == 'ok', -r['recs']))
    empty = [r for r in rows if r['res']['sans allergie']['status'] != 'ok']
    lines = ['# Recettes : ingrédients trouvés en magasin', '',
             f'Contrôle du {datetime.date.today().strftime("%d/%m/%Y")}, appli {version} : {len(rows)} ingrédients achetés en magasin, '
             f'{len(rows) - len(empty)} trouvés sans allergie.', '',
             '| Ingrédient | Recettes | ' + ' | '.join(l for l, _ in PROFILES) + ' |', '|---|---:|' + '---|' * len(PROFILES)]
    for r in rows:
        cells = []
        for lab, _ in PROFILES:
            x = r['res'][lab]
            cells.append({'ok': f"{x['n']} produits", 'check': 'à vérifier', 'no': '**aucun**'}.get(x['status'], x['status']))
        lines.append(f"| {r['n']} | {r['recs']} | " + ' | '.join(cells) + ' |')
    report = '\n'.join(lines) + '\n'
    open(OUT, 'w', encoding='utf-8').write(report)
    if os.environ.get('GITHUB_STEP_SUMMARY'):
        open(os.environ['GITHUB_STEP_SUMMARY'], 'a', encoding='utf-8').write(report)
    print('\n'.join(lines[:3]))
    for r in empty:
        print(f"  RIEN : {r['n']} ({r['id']}), {r['recs']} recette(s)")
    print('Contrôle OK' if not empty else f'{len(empty)} ingrédient(s) sans produit')
    sys.exit(1 if empty else 0)


if __name__ == '__main__':
    main()
