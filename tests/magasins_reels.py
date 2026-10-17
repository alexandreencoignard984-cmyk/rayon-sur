"""Vraie base data/stores/ servie en local : Rennes, Paris, Avranches."""
import os, sys, re, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import localisation as N
from playwright.sync_api import sync_playwright
orig = N.setup_routes
def routes(ctx, mode):
    ov = orig(ctx, mode)
    ctx.unroute(re.compile(r'.*/data/stores/.*'))
    return ov
N.setup_routes = routes
httpd, base = N.serve()
with sync_playwright() as p:
    b = p.chromium.launch()
    for name, pos in [('Rennes', (48.1113, -1.68)), ('Paris', (48.8566, 2.3522)), ('Avranches', (48.6844, -1.3569))]:
        ctx, page, errs, ov = N.new_page(b, base, geo=pos)
        page.wait_for_function("() => window.__RS && __RS.nearIds().length > 0", timeout=15000)
        st = page.evaluate("() => ({ ids:__RS.nearIds(), near:__RS.getNear() })")
        n = st['near']
        print(f"{name} : {n['r']} km, source {n['from']}, {len(st['ids'])} enseignes : " + ', '.join(f"{i} {n['stores'][i]['dist']:.1f}" for i in st['ids']))
        N.check(n['from'] == 'base' and ov['n'] == 0, 'base de l\'appli utilisée, aucun appel Overpass')
        N.check(not errs, 'aucune erreur JavaScript' + (': ' + '; '.join(errs[:3]) if errs else ''))
        ctx.close()
    b.close()
httpd.shutdown()
print('TOUT EST OK' if not N.FAIL else f'{len(N.FAIL)} ÉCHEC(S)')
sys.exit(1 if N.FAIL else 0)
