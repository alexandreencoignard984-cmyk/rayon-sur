# Rayon sûr : guide pour travailler sur l'appli

Appli web en français, pour iPhone avant tout : elle trouve les produits de supermarché compatibles avec les
allergies de l'utilisateur, par magasin et par rayon, scanne les codes-barres, garde une liste de courses et
propose des recettes. En ligne : https://alexandreencoignard984-cmyk.github.io/rayon-sur/ (GitHub Pages, branche
`main`, publiée à chaque push).

Utilisateur et propriétaire : Alexandre, non développeur. Il écrit en français familier mais attend un résultat
professionnel. Il utilise un iPhone (Safari, parfois en navigation privée, et les navigateurs intégrés de
Snapchat ou de Claude).

## Règles qui priment sur tout

1. **Sécurité alimentaire.** Un produit marqué « Compatible » alors qu'il contient un allergène du profil est le
   pire bug possible. En cas de doute (ingrédients absents, traces, données incomplètes), le produit va dans
   « À vérifier », jamais dans « Compatible ». Ne jamais assouplir la détection pour afficher plus de produits.
2. **Ne jamais perdre les données de l'utilisateur.** Tout est dans `localStorage` (clés `rs2:*` : profil,
   liste, favoris, historique, recettes, position…). Un changement de format doit relire l'ancien format.
   Les fonctions `clean*` au chargement nettoient les données abîmées : les garder.
3. **Pas de service worker, de cache hors ligne ni de logique de version** sans l'accord d'Alexandre (il a déjà
   refusé un correctif de ce type).
4. **Pas de pistage, de statistiques d'usage, de compte, de service payant ni de collecte de données.**
5. Pas de nouvelle bibliothèque externe sauf nécessité réelle. CDN autorisés : cdnjs, jsdelivr, unpkg (version
   exacte). Polices : Google Fonts.

## Architecture

- **`index.html`** : toute l'appli (≈ 300 Ko) — HTML, CSS et un seul gros script (IIFE) en JS sans framework.
  Les lignes 15 et 16 contiennent l'icône en base64 (très longues) : ne pas les lire en entier, utiliser
  `grep -n` et `sed -n 'a,bp'` sur des plages, ou couper l'affichage (`cut -c1-300`).
- Version affichée : `const APP_VERSION = '3.x'` (Profil). L'augmenter à chaque publication et mettre à jour
  l'attente dans `tests/appli.py` si besoin.
- Écrans (`#screen-search`, `recipes`, `scan`, `list`, `profile`) changés par `go(name)`. L'écran Rechercher a deux
  vues (`setSearchView('home' | 'results')`) : l'accueil avec les rayons courants en tuiles (`HOME_AISLES`) et
  les résultats ; le geste retour et l'onglet retouché ramènent à l'accueil. Au démarrage : toujours l'accueil. Fiches (`dialog.sheet`)
  ouvertes et fermées par `openDialog(d)` / `closeDialog(d)` : elles gèrent l'historique, donc le geste retour
  de l'iPhone ferme la fiche. Messages : `toast(msg, ms, { label, fn })`.
- **Mise en page d'appli** : seul `#scroller` défile, la page entière jamais ; la barre d'onglets est dans le
  flux, pas en `position: fixed`. Raison : iOS 26 décale les éléments fixés en bas quand la barre d'adresse se
  replie ou après le clavier. Ne pas revenir à un défilement de la page ; faire défiler avec `scrollBox()`.
- Verdict allergènes : `evaluate(p)` et le profil `profile`. Drive : `DRIVES`, `driveMode`, `driveUrl`,
  `driveTerms`, `linkChains`, `driveCard` (code-barres pour Carrefour, Leclerc, Cora ; Google + code-barres pour
  Intermarché ; recherche par nom ailleurs). Magasins proches : `computeNear`, `placesAround`, tuiles
  `data/stores/`. Position : `getPosition`, `autoLocate`, adresse enregistrée en repli.
- `window.__RS` expose des fonctions pour les tests.
- **Données** : `data/index.json` + `data/a/<rayon>.json` (produits Open Food Facts rangés par rayon, mis à jour
  chaque lundi par `.github/workflows/data.yml` → `tools/build_data.py`, réglages dans `tools/config.json`) ;
  `data/stores/` (magasins OpenStreetMap, `stores.yml` → `tools/build_stores.py`). Ne pas modifier ces fichiers
  de données à la main.
- Les sites des drives bloquent les robots : impossible de vérifier leurs résultats automatiquement. La page
  Profil › « Tester les liens drive » sert au test à la main.

## Vérifier et tester

- Syntaxe JS : `python3 tools/check_js.py` (extrait les scripts et lance `node --check`).
- Tests (Playwright Python + Chromium déjà installé dans `/opt/pw-browsers`, ne pas lancer
  `playwright install`) : `bash tests/run.sh` (≈ 10 min), ou un fichier seul : `python3 tests/navigation.py`.
  Si Playwright manque : `pip install playwright==1.56.0 --break-system-packages`.
  - `verdicts.py` : verdicts allergènes (mots-clés, faux amis, règles de sécurité). À compléter à chaque
    changement du verdict.
  - `localisation.py` : position, adresse, magasins, horaires, liens drive. Contient aussi les outils communs
    (`serve`, `new_page`, `setup_routes` qui simule les services externes, `check`, `wait_near`, `RENNES`).
  - `navigation.py` : retour, onglets, recettes, messages, carte drive, barre du bas, positions par onglet.
  - `liens_drive.py`, `magasins_reels.py`, `appli.py`, `bugs.py`, `robustesse.py` (données abîmées et clics au
    hasard, hors ligne compris).
- `python3 tools/audit_drive.py` : contrôle les recherches drive sur toute la base (seuils dans le fichier).
- Toute correction de bug ou nouvelle fonction vient avec un test. Toute erreur JavaScript fait échouer les tests.
- Regarder le résultat : captures Playwright à 390 × 844 (taille iPhone), en clair et en sombre.
- À chaque push sur `index.html` ou `tests/`, la tâche GitHub « Tests » relance tout (`gh run list`).

## Style de l'interface

- Français simple, tutoiement, phrases courtes, aucun jargon technique. L'utilisateur doit comprendre chaque
  écran sans explication.
- iPhone d'abord (390 px de large, zones tactiles ≥ 44 px), mode sombre géré par les variables CSS de `:root`.
- Garder le style existant (couleurs, cartes, puces, fiches qui montent du bas).

## Publier

- Commit avec `git -c user.name="Claude" -c user.email="noreply@anthropic.com" commit`, message en français qui
  explique le changement pour Alexandre, terminé par les lignes d'attribution demandées par la session.
- `git pull --rebase origin main` puis `git push origin HEAD:main`. Jamais de `--force`, jamais de réécriture
  de l'historique. Si la tâche « Tests » échoue après le push : corriger tout de suite, sinon `git revert`.
- Journal des améliorations, pistes et décisions en attente : `rapports/journal-ameliorations.md`.
