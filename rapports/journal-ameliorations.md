# Journal des améliorations

Tenu par les séances d'amélioration automatique (et à la main). Chaque séance lit ce fichier avant de commencer
et le met à jour à la fin : c'est la mémoire d'une séance à l'autre.

## À décider par Alexandre

Rien de cette liste n'est fait sans son accord.

- **Mode hors ligne** (service worker) : garder l'appli et la liste utilisables sans réseau. Proposé, pas encore
  accepté ; un correctif de cache par version a déjà été refusé.
- **Naturalia et mise en avant des magasins bio** : proposé, en attente de réponse.

## Pistes

Idées notées, à reprendre par ordre d'intérêt pour l'utilisateur. Retirer une piste une fois faite ou abandonnée.

- Vérifier que la barre du bas reste en bas sur iPhone (corrigé en 3.12 sans test sur un vrai téléphone) ;
  surveiller aussi le clavier dans les fiches (champ adresse), même bug possible sous iOS 26.
- Recherche par code-barres chez Carrefour et Leclerc : non vérifiable automatiquement ; attendre le rapport de
  « Tester les liens drive » et corriger les enseignes qui échouent.
- Premier lancement : compter les étapes jusqu'au premier résultat utile et les réduire si possible.
- Accessibilité : contrastes en mode sombre, libellés des boutons icône, taille des zones tactiles.
- Faux doutes restants après la 3.13 : desserts végétaux appelés « Skyr », barres « nougat » sans fruits à coque
  (Mars). Sans danger (« À vérifier »), mais on pourrait les lever avec le label végan ou la liste d'ingrédients.
- Faux doutes ajoutés en 3.14 (sans danger, « À vérifier ») : madeleines ou cookies sans gluten qui ne disent pas
  « sans gluten » dans les ingrédients, tranches végétales « saveur emmental », sirop « saveur spéculoos ». On
  pourrait les lever avec le label « sans gluten » / végan d'Open Food Facts.
- Mollusques : les « coques » ne sont pas reconnues (le mot se confond avec « fruits à coque », présent dans
  16 000 fiches). À faire avec une règle qui écarte « fruits à coque ».
- Tâches programmées de GitHub très en retard (la « Base produits » prévue à 3 h 17 UTC a démarré à 8 h 46) :
  vérifier chaque semaine que les bases ont bien été mises à jour, sinon les lancer à la main.

## Journal

### 2026-10-19 (2e séance) · 3.14
- **Verdict allergènes encore plus sûr.** Des produits sortaient « Compatible » alors qu'ils contiennent ce que
  l'utilisateur évite, parce que l'ingrédient était écrit d'une façon que l'appli ne reconnaissait pas. Ils passent
  maintenant dans « À vérifier » :
  - **lait** : fromages nommés sans le mot « lait » (emmental, parmesan, grana padano, cheddar, comté, feta, chèvre,
    raclette, stracciatella, béchamel…). Exemples corrigés : « Pizza 4 saisons Bio » (emmental), « Pesto Rosso »
    (parmesan), « Taboulé au cheddar ». 187 produits.
  - **sulfites** écrits « disulfite de potassium » ou « metabisulphite » (jus de citron, sirops…) : 922 produits.
  - **gluten** : biscuits, cookies, gaufrettes, madeleines, brioches, spéculoos, croûtons, génoise : 248 produits.
  - **poisson** : morue (accras, brandade, foie de morue), sébaste, capelan… : 50 produits.
  - **arachide** écrite « cacahouète » ; **crustacés** : araignée de mer.
  - Les beurres de cacahouète ne sont plus pris pour du beurre (lait), et « Franche-Comté » pour du comté.
- **Ma liste, « meilleur choix »** : à égalité, le magasin le plus proche passe devant (avant : Super U à 8,6 km
  devant Carrefour à 550 m parce que le produit y avait été vu). Les deux restent marqués « Meilleur choix ».
- Le message « Ajouté à ta liste · Voir ma liste » disparaît quand on change d'onglet (il restait affiché sur
  Ma liste elle-même).
- Tests : `tests/verdicts.py` (nouveaux mots), `tests/localisation.py` (13b), `tests/navigation.py` (5).

### 2026-10-19 · 3.13
- **Verdict allergènes plus sûr.** Quand la fiche Open Food Facts ne déclare pas l'allergène, l'appli repère
  maintenant beaucoup plus d'ingrédients à risque et classe le produit « À vérifier » au lieu de « Compatible » :
  poissons (limande, églefin, lieu noir, sauce Worcestershire…), mollusques (Saint-Jacques, bulots, calamars…),
  œufs (mayonnaise, meringue, ovoproduits), gluten (pain, chapelure, semoule, couscous, boulgour, seitan), soja
  (miso, tamari), sulfites écrits « E-223 »… Sur toute la base, plus de 800 verdicts corrigés ; par exemple un
  « Filet de limande meunière » sortait « Compatible » pour une allergie au poisson. Les faux amis restent
  compatibles : lait de coco, noix de coco, caviar d'aubergines, semoule de maïs, chapelure sans gluten ; et les
  noix de Saint-Jacques ne sont plus prises pour des fruits à coque (105 produits).
- **Recherche par nom dans un rayon** : un bouton « Chercher « … » dans tous les rayons » apparaît, et le message
  quand rien n'est compatible l'indique. Accords corrigés (« 1 produit analysé »).
- Tests : `tests/verdicts.py` (mots-clés, faux amis, règles de sécurité).

### 2026-10-17 · 3.12
- Barre d'onglets toujours en bas : la page ne défile plus, seul le contenu défile (bug iOS 26 des éléments
  fixés en bas). Chaque onglet garde sa position ; retoucher l'onglet ouvert remonte en haut.
- Aide « Le site bloque ou affiche « Vérification de sécurité » ? » dans Stock au drive, avec « Copier le lien ».

### 2026-10-17 · 3.11
- Liens drive par code-barres (Carrefour, Leclerc, Cora), Google + code-barres pour Intermarché, lien de secours.
- « Vu dans cette enseigne » / « Pas signalé ici ». Geste retour qui ferme les fiches. « Voir ma liste » dans les
  messages. Fiche produit simplifiée, mode d'emploi en 3 étapes, résumé en tête de Ma liste.
