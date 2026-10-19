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
- Verdict allergènes : `evaluate(p)` et le profil `profile`. Il tient compte aussi des allergènes repérés par Open Food
  Facts dans les ingrédients (`_ia`), de la fiabilité de la liste (`_q` : « i » à compléter, « u » mal lue) et des
  produits signalés par l'utilisateur (`flags`, clé `rs2:flags`, toujours « Exclu »). À l'ouverture d'une fiche,
  `refreshLive` recharge la version actuelle d'Open Food Facts et recalcule le verdict partout. Drive : `DRIVES`, `driveMode`, `driveUrl`,
  `driveTerms`, `linkChains`, `driveCard` (code-barres pour Carrefour, Auchan, Super U, Biocoop, Cora ; Google +
  code-barres pour Intermarché, dont la recherche n'a pas d'adresse ; Leclerc : la recherche de e.leclerc ne montre pas les courses ; si l'utilisateur a indiqué son drive
  (Profil › « Mon drive Leclerc », adresse collée, clé `rs2:leclerc` `{id, id2, name}`, `parseLeclerc`), recherche
  directe `m-courses.leclercdrive.fr/magasin-<id>-<id2>/recherche/<texte>`, sinon l'accueil du drive s'ouvre et le nom
  est copié (`data-cp`) ; Lidl, Aldi, Netto : pas de lien, « à prendre en magasin » ; Picard : nom sans la marque ; recherche par
  nom ailleurs, avec la marque du paquet et non le fabricant : `BRAND_GROUP`). La carte montre d'abord les enseignes où le produit a été vu, les
  autres repliées (`.dmore`). « Mauvais produit ? » enregistre une autre recherche par produit et enseigne
  (`driveFix`, clé `rs2:drivefix` : `"code|enseigne": "nom" | "marque"`), prioritaire dans `driveMode`. Magasins proches : `computeNear`, `placesAround`, tuiles
  `data/stores/`. Position : `getPosition`, `autoLocate`, adresse enregistrée en repli.
- Recettes : `ING` (ingrédients → catégories de la base) et `RECIPES` (93 recettes : `g` rubrique, `e` pictogramme,
  `t` minutes, `st` étapes, `i` ingrédients `[id, quantité pour 4, unité, facultatif]`). La page d'une recette a deux
  onglets (`recTab('recipe' | 'products')`) : « La recette » (ingrédients, quantités, étapes) s'ouvre par défaut. Un ingrédient qui pointe vers
  une catégorie absente de la base doit l'ajouter dans `tools/config.json` (`extra`).
- `window.__RS` expose des fonctions pour les tests.
- **Données** : `data/index.json` + `data/a/<rayon>.json` (produits Open Food Facts rangés par rayon, mis à jour
  chaque lundi par `.github/workflows/data.yml` → `tools/build_data.py`, réglages dans `tools/config.json`) ;
  `data/stores/` (magasins OpenStreetMap, `stores.yml` → `tools/build_stores.py`). Ne pas modifier ces fichiers
  de données à la main.
- Les sites des drives bloquent l'atelier de Claude. La tâche GitHub « Sonde drive » (`tools/sonde_drive.py`,
  `.github/workflows/sonde.yml`, lancée par `gh api -X POST repos/<dépôt>/actions/workflows/sonde.yml/dispatches -f ref=main`)
  ouvre les vrais sites depuis GitHub et publie rapport et captures sur une branche `sonde-drive-<n°>` (à lire avec
  `git fetch origin sonde-drive-<n°>`). Carrefour (souvent), Auchan, Biocoop, Picard, Lidl répondent ; Super U, Intermarché,
  Monoprix et le drive Leclerc bloquent ces serveurs. Mode `adresses` pour tester un format de lien. La page
  Profil › « Tester les liens drive » sert au test à la main.

## Vérifier et tester

- Syntaxe JS : `python3 tools/check_js.py` (extrait les scripts et lance `node --check`).
- Tests (Playwright Python + Chromium déjà installé dans `/opt/pw-browsers`, ne pas lancer
  `playwright install`) : `bash tests/run.sh` (≈ 10 min), ou un fichier seul : `python3 tests/navigation.py`.
  Si Playwright manque : `pip install playwright==1.56.0 --break-system-packages`.
  - `verdicts.py` : verdicts allergènes (mots-clés, faux amis, règles de sécurité). À compléter à chaque
    changement du verdict.
  - `fiches.py` : allergènes repérés mais non déclarés, listes incomplètes, signalement, fiche mise à jour en direct.
  - `recettes.py` : catalogue des recettes (ingrédients connus, étapes, temps), filtres, préparation.
  - `localisation.py` : position, adresse, magasins, horaires, liens drive. Contient aussi les outils communs
    (`serve`, `new_page`, `setup_routes` qui simule les services externes, `check`, `wait_near`, `RENNES`).
  - `navigation.py` : retour, onglets, recettes, messages, carte drive, barre du bas, positions par onglet.
  - `liens_drive.py`, `magasins_reels.py`, `appli.py`, `bugs.py`, `robustesse.py` (données abîmées et clics au
    hasard, hors ligne compris).
- `python3 tools/audit_drive.py` : contrôle les recherches drive sur toute la base (seuils dans le fichier).
- `python3 tools/audit_recettes.py` : chaque ingrédient des recettes doit trouver des produits (sans allergie, puis
  lait, gluten, œufs, fruits à coque) ; écrit `rapports/recettes.md`. Lancé aussi par la tâche « Tests ».
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
