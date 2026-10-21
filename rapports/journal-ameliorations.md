# Journal des améliorations

Tenu par les séances d'amélioration automatique (et à la main). Chaque séance lit ce fichier avant de commencer
et le met à jour à la fin : c'est la mémoire d'une séance à l'autre.

## À décider par Alexandre

Rien de cette liste n'est fait sans son accord.

- **Mode hors ligne** (service worker) : garder l'appli et la liste utilisables sans réseau. Proposé, pas encore
  accepté ; un correctif de cache par version a déjà été refusé.
- **Naturalia et mise en avant des magasins bio** : proposé, en attente de réponse.
- **Accès GitHub des séances automatiques** (21/10) : la séance n'a pas pu publier ni lire les tâches GitHub
  (« dépôt non autorisé pour cette session »). Rajouter le dépôt rayon-sur aux sources de la tâche programmée.
- **Thème « Comme l'iPhone » par défaut** : aujourd'hui l'appli démarre en « Clair » même si l'iPhone est en sombre.
- **Vins « sans sulfites ajoutés »** : restent « Compatible » grâce au nom ; ils en contiennent souvent un peu
  naturellement. Les passer « À vérifier » ?

## Pistes

Idées notées, à reprendre par ordre d'intérêt pour l'utilisateur. Retirer une piste une fois faite ou abandonnée.

- Vérifier que la barre du bas reste en bas sur iPhone (corrigé en 3.12 sans test sur un vrai téléphone) ;
  surveiller aussi le clavier dans les fiches (champ adresse), même bug possible sous iOS 26.
- Recherche par code-barres chez Carrefour et Leclerc : non vérifiable automatiquement ; attendre le rapport de
  « Tester les liens drive » et corriger les enseignes qui échouent. Depuis la 3.20, Alexandre signale les mauvais
  liens avec « Mauvais produit ? » (clé `rs2:drivefix`, sur son téléphone seulement) : s'il en cite, regarder si une
  enseigne revient souvent et changer sa recherche par défaut (`driveMode`).
- Drive Leclerc (3.23) : l'utilisateur colle l'adresse de son drive. Demander à Alexandre si la recherche directe
  s'ouvre bien sur son iPhone ; sinon revenir à l'accueil + nom copié. Un numéro de drive automatique par magasin
  demanderait une liste des drives (l'API Leclerc est protégée, et leurs pages interdisent les robots).
- Super U, Monoprix, Intermarché et drive Leclerc bloquent la sonde depuis GitHub : seuls les retours d'Alexandre
  (« Mauvais produit ? », « Tester les liens drive ») peuvent confirmer leurs liens.
- Mascarpone et cerneaux de noix : aucune version pour les allergiques au lait / aux fruits à coque (normal, l'appli
  le dit) ; on pourrait proposer un remplaçant (fromage végétal à tartiner) si la base en a.
- Accueil (3.14) : voir si d'autres rayons méritent une tuile, et s'il faut afficher sur chaque tuile le nombre de
  produits compatibles avec le profil (calcul à faire sans ralentir l'ouverture).
- Accessibilité : en clair, `--ok` sur `--ok-bg` à 4,36:1 (« Meilleur choix », « Modifier ») ; boutons « Ajouter /
  Favori / Partager » de la fiche sans forme visible en clair (`.act` : `--surface` → `--sunk`) ; zones tactiles
  sous 44 px : « Itinéraire » (`.loclist a`), `.selchip`, `.pchip`, `.nearline`, liens du pied de page Profil.
- Allergène écrit en clair dans les ingrédients (« SÉSAME », « purée de sésame ») mais non déclaré par Open Food
  Facts : « À vérifier » ; on pourrait le passer « Exclu » hors des phrases de traces (le client hésite).
- Ajouter un produit « Exclu » à la liste ne prévient pas (« Ajouté à ta liste ») : afficher un avertissement.
- Position refusée : magasin Leclerc imposé, « Magasins près de moi » introuvable à l'accueil ; la carte drive ne
  montre alors que Leclerc (ajouter les enseignes où le produit a été vu, phrase au singulier).
- Recettes : ingrédient sans version compatible (moutarde, tahini) sans idée de remplacement.
- Petits textes : « Charger tout le rayon » ≠ bouton « Tout le rayon » ; tuile « Apéritif » → titre « Snacks salés » ;
  étiquettes d'allergènes non traduites (« Metabisolfito ») ; « Mon drive Leclerc » : bulle du navigateur au lieu du
  message de l'appli pour un texte qui n'est pas une adresse.
- Garde-fous par rayon (3.26) : faux doutes sans danger « Tendre Noix » (jambon), « Pistaches coques », thon
  végétal ; risque faible noté : `_fresh` accepté pour tout code dans `cleanP` (limiter aux codes `f:`).
- Faux doutes restants après la 3.13 : desserts végétaux appelés « Skyr », barres « nougat » sans fruits à coque
  (Mars). Sans danger (« À vérifier »), mais on pourrait les lever avec le label végan ou la liste d'ingrédients.
- Faux doutes ajoutés en 3.14 (sans danger, « À vérifier ») : madeleines ou cookies sans gluten qui ne disent pas
  « sans gluten » dans les ingrédients, tranches végétales « saveur emmental », sirop « saveur spéculoos ». On
  pourrait les lever avec le label « sans gluten » / végan d'Open Food Facts.
- Tâches programmées de GitHub très en retard (la « Base produits » prévue à 3 h 17 UTC a démarré à 8 h 46) :
  vérifier chaque semaine que les bases ont bien été mises à jour, sinon les lancer à la main.
- Ingrédients en langue étrangère (3.24) et mots mal lus (3.25) : faux doutes connus, sans danger : « ei » (œuf en
  allemand) quand l'étiquette mal lue écrit « ei » pour « et », mentions de traces (« senza glutine, arachidi »),
  « oester-zwam » (pleurote), « bie » qui peut être autre chose que « blé ». Refaire la recherche des mots mal lus
  (mots à une lettre près d'un allergène, voir la séance du 20/10) après les grosses mises à jour de la base.

## Journal

### 2026-10-21 · 3.26 — séance de 11 h 40 (heure de Paris)
- **Publiée le 21/10 à 16 h 08** (heure de Paris) par une autre séance : la séance de 11 h 40 n'avait pas l'accès
  GitHub (push et `gh` en 403) ; son patch a été appliqué tel quel (`git am`, commit fc365c6) après `check_js.py`,
  `tests/run.sh` et `audit_drive.py` au vert. Tâches GitHub « Tests » et « pages build and deployment » réussies
  sur ce commit.
- **Sécurité (sulfites)** : « disulphite », « metbisulphite », « anydride sulfureux », « SO2 », mots collés
  (« etsulfites »), langues étrangères, et « d_isulfite_ » coupé par Open Food Facts n'étaient pas reconnus : TUC,
  Maille Dijon, biscuits Gullón, abricots secs, crevettes sortaient « Compatible ». Les vins passent « À vérifier ».
- **Sécurité (poisson)** : raie, sole, bar (par le rayon), loup de mer, roussette, tacaud, omble, œufs de lompe,
  anchoïade non reconnus ; tout produit des rayons poissons / produits de la mer reste « À vérifier » sans mot trouvé.
- **Sécurité (moutarde, céleri, arachide)** : « mustardseeds », « mosterd », « sennep » (nordique), « célerie »,
  « selleri », « celer », « peanut butter »… reconnus. Un nom « vegan » ou « végétal » n'efface plus l'indice du nom
  que pour le lait et les œufs (« Vegan Protein Bar Peanut Butter » était « Compatible » pour l'arachide). Rayon
  moutardes → « À vérifier » pour la moutarde.
- **Sécurité (chiffre de note collé)** : « oeufs1 », « ŒUF1 », « poisson1 », « Cacahuètes1 » reconnus.
- Sur la base : Compatible → À vérifier : poisson 759, sulfites 214, moutarde 40, céleri 35, arachide 24, autres
  ≤ 11. Aucun produit ne gagne « Compatible ».
- Recettes : le compteur « Les produits 7/7 » (ou 12/11) comptait le sel et le poivre ; corrigé.
- Recherche : choisir un rayon après une recherche par nom ne garde plus le texte (« 0 produit pour « houmous » »).
- Mode sombre : chiffres et symboles foncés sur les pastilles vertes / orange / rouges (contraste 2 → 8) ; cercles à
  cocher de Ma liste bien visibles (1,25 → 5,3).
- Tests : `verdicts.py` (≈ 80 cas), `recettes.py`, `navigation.py` (rayon, contrastes) ; délai de `robustesse.py`
  porté à 30 min dans `run.sh` (il frôlait 20 min).
- Agents : DÉTECTEUR — sulfites, poissons, chiffres collés, moutarde/céleri étrangers, vins ; bases à jour (19/10) ;
  GitHub inaccessible. PARCOURS CLIENT (arachide + sésame + moutarde, puis céleri + sulfites, Lyon/Bordeaux) — mêmes
  verdicts, compteur recettes, rayon qui garde la recherche, plusieurs gênes (voir Pistes) ; aucune erreur JS.
  DESIGN — contrastes sombres et cercles de Ma liste (faits), boutons de fiche en clair et petites zones (Pistes).

### 2026-10-20 · 3.25
- Demande d'Alexandre : « continue à corriger tant qu'il reste un détail qui ne fonctionne pas ».
- **Sécurité (mots mal lus sur l'étiquette)** : recherche dans toute la base des mots à une lettre près d'un allergène.
  Reconnus maintenant : « doeuf », « d'eufs », « oeuts », « aeufs », « lalt », « iait », « lactoserun », « qluten »,
  « giuten », « darachides », « sesane », « motarde », « nolsettes »… Sur la base actuelle : 256 produits de moins
  « Compatible » pour les œufs, 38 pour le lait, 19 pour le gluten, 6 à 17 pour les autres. Faux amis gardés :
  « beure de cacao », « huile de nolx de coco ».
- La raison précise l'allergène aussi pour les mots étrangers déjà connus : « LECHE » (lait ?).
- **Recettes** : quand l'appli remplace un ingrédient, la préparation le rappelle au-dessus des étapes (« Pour toi,
  dans les étapes : lait → une boisson végétale, beurre → une margarine »), car les étapes parlent toujours du lait
  et du beurre. Pour une allergie au gluten, la farine est annoncée « farine sans gluten » (« autre farine » avant).
- Tests : `verdicts.py` (mots mal lus, raison), `recettes.py` (rappel des remplacements).

### 2026-10-20 · 3.24
- **Sécurité (œufs)** : sur environ 500 fiches, l'étiquette photographiée a été mal lue et « ŒUFS » est devenu « CEUFS »
  (madeleines, salades, quiches…). L'appli ne reconnaissait pas le mot : ces produits sortaient « Compatible » pour une
  allergie aux œufs. Ils passent « À vérifier ».
- **Sécurité (listes en langue étrangère)** : beaucoup de produits vendus en France ont une fiche remplie depuis
  l'étiquette espagnole, italienne, allemande, néerlandaise ou portugaise (« harina de TRIGO », « Weizenmehl »,
  « Magermilchpulver », « nocciole », « Sojalecithin »…). Ces mots n'étaient pas reconnus : des biscuits María au blé
  ou des Pringles à l'amidon de blé sortaient « Compatible » pour le gluten. L'appli connaît maintenant les mots de
  ces langues pour les 14 allergènes, y compris dans les mots composés allemands, sans confondre les faux amis
  (sarrasin, lait de coco, beurre de cacao, acide lactique, noix de muscade, cumin…). Sur la base actuelle :
  137 produits de moins « Compatible » pour le gluten, 52 pour le lait, 693 pour les œufs (surtout « CEUFS »), 204
  pour les fruits à coque, 315 pour le soja, entre 12 et 134 pour les autres. Aucun produit ne gagne « Compatible ».
- La raison affichée précise l'allergène pour ces mots : « Ingrédient à vérifier : « TRIGO » (gluten ?) », et le mot
  est surligné dans la liste d'ingrédients. Une liste illisible dit maintenant « Ingrédients illisibles ou dans une
  autre langue » au lieu de « non renseignés ».
- Tests : `verdicts.py` (80 nouveaux cas : mots étrangers, mots composés, faux amis, message affiché).

### 2026-10-19 · 3.23
- Demande d'Alexandre : « corrige et cherche des solutions pour tous les problèmes ».
- **Mon drive Leclerc** (Profil, ou depuis la ligne Leclerc d'une fiche) : l'utilisateur colle une fois l'adresse de
  son drive ; les liens Leclerc ouvrent alors directement la recherche du produit dans son magasin
  (`m-courses.leclercdrive.fr/magasin-<n°>-<n°>/recherche/<texte>`, format relevé en vrai par le projet libre
  « Comparateur de paniers », août 2026). Sauvegardé dans l'export. Non vérifiable depuis GitHub (DataDome).
- **Super U** : recherche par code-barres (Courses U trouve le produit exact par son EAN, vérifié en vrai le
  01/09/2026 par le même projet). **Biocoop** : code-barres aussi (sonde : fiche exacte 6 fois sur 10, sinon « aucun
  résultat exact » ; la recherche par nom ouvrait parfois une page de conseils).
- Sonde avec vrai navigateur et rythme lent : Super U, Intermarché, Monoprix et le drive Leclerc bloquent toujours les
  serveurs de GitHub. Intermarché : sa recherche n'a pas d'adresse (`/recherche` renvoie une erreur) et la fiche
  produit exige le nom exact dans l'adresse (`/produit/<nom>/<EAN>`) : on garde Google + code-barres.
- **Sécurité (mollusques)** : les « coques » (coquillages), « amandes de mer », berniques, patelles, clovisses, bulots
  anglais (whelks)… n'étaient pas reconnus : des rillettes d'amandes de mer ou une boîte de coques pouvaient sortir
  « Compatible ». Corrigé, sans confondre avec les fruits à coque (même mal écrits), l'œuf à la coque, les coques en
  chocolat ou de macaron. 150 produits passent en « À vérifier » pour les mollusques.
- Recettes : nouveau contrôle `tools/audit_recettes.py` (aussi dans la tâche « Tests ») : les 106 ingrédients achetés
  en magasin trouvent des produits. Mayonnaise sans œuf proposée aux allergiques aux œufs.
- Zones tactiles : puces, petits boutons, boutons + et − des recettes, liens de Ma liste, titres repliables passent à
  44 px touchables sans changer le dessin.

### 2026-10-19 · 3.22
- Deuxième sonde après la 3.21 : Auchan trouve le bon produit 5 fois sur 5 (0 avant), Picard 5 sur 5 (le velouté bio
  n'ouvre plus le rayon bio), Carrefour 4 sur 4. Le drive Leclerc, Super U, Intermarché et Monoprix bloquent les
  serveurs de GitHub : non vérifiables ainsi.
- Lidl, Aldi, Netto : leur site ne vend pas les courses (la recherche « Cristaline » ou « Pesto » montrait une cocotte,
  des pommes de terre en promo, des vêtements). Plus de lien vers leur site : la fiche dit « Vu dans cette enseigne ·
  à prendre en magasin », et Ma liste n'a plus de bouton « drive » pour eux.
- La phrase d'aide de la carte ne parle plus de « Voir le produit » quand aucun bouton visible ne l'affiche.

### 2026-10-19 · 3.21
- Demande d'Alexandre : « continue à corriger les liens vers les drives, que tout soit bien ».
- **Sonde des vrais sites** (nouvelle tâche GitHub « Sonde drive ») : 95 pages ouvertes comme un iPhone depuis GitHub.
  Constats : la recherche de **e.leclerc** montre des livres, des LEGO, des cahiers (c'est le site non alimentaire) et
  rien pour un code-barres ; **Auchan** trouve le produit exact par code-barres (4 sur 5) et dit « rien trouvé »
  sinon, alors que sa recherche par nom ratait ; **Carrefour** par code-barres : le bon produit à chaque fois ; les
  recherches par nom échouaient avec le nom du fabricant (« Mondelez Prince » : rien chez Super U ni Auchan,
  « Lindt & Sprüngli » : 0 résultat chez Carrefour) ; **Picard** : « Le Bio par Picard … » ouvrait le rayon bio, et le
  code-barres n'y marche pas.
- Corrections : Leclerc ouvre le site du **drive Leclerc** et copie le nom du produit à coller dans sa recherche ;
  Auchan passe au code-barres ; la recherche par nom prend la marque du paquet (LU, Lindt, Nutella, Activia…) au lieu
  du fabricant, et sans « goût », « saveur », « parfum » ; Picard sans la marque ; « Coca-Cola Coca-Cola » corrigé.
- « Mauvais produit ? » n'apparaît plus quand il n'existe pas d'autre recherche ; bouton agrandi (44 px).
- Tests : `liens_drive.py` (liens d'après la sonde, copie du nom pour Leclerc, marques), attentes Leclerc mises à jour.

### 2026-10-19 · 3.20
- Demande d'Alexandre : « je veux aussi la recette » et « beaucoup de produits sont redirigés vers des mauvais
  produits ou de mauvaises catégories dans les drives ».
- **La recette d'abord** : la page d'une recette s'ouvre sur l'onglet « La recette » (ingrédients avec quantités
  pour le nombre de personnes choisi, état de chaque ingrédient pour le profil, étapes numérotées). L'onglet « Les
  produits » garde le choix des produits en magasin ; le bouton « Voir les produits sans tes allergènes » y mène.
- **Liens drive plus justes** : sur la fiche, seules les enseignes où le produit a été vu sont proposées d'emblée ;
  les autres sont repliées sous « Chercher aussi chez … » avec la mise en garde « peut-être pas vendu ici ». Un
  produit vu nulle part l'annonce clairement. Chaque lien a un bouton « Mauvais produit ? » : l'appli retient,
  pour ce produit et cette enseigne, une autre recherche (code-barres → nom → toute la marque) et l'ouvre tout de
  suite ; « Revenir au premier lien » annule. Ces choix sont dans la sauvegarde (export / import).
- « Ma liste chez … » : les produits vus dans l'enseigne en premier, ceux d'une marque d'une autre enseigne à la fin.
- Tests : `liens_drive.py` (carte drive, signalement, ordre de la liste), `bugs.py` (sauvegarde), `robustesse.py`
  (`rs2:drivefix` abîmé), `recettes.py` (onglets).

### 2026-10-19 · 3.19
- Recettes : la chapelure pointait vers une catégorie vide (« en:breadcrumbs ») ; elle cherche maintenant dans
  « en:bread-crumbs » puis dans le rayon pain. Pois chiches (464 produits), quinoa (406) et cacao (1 077) trouvés.

### 2026-10-19 · 3.18
- **Recettes bien plus complètes** : 93 recettes (61 nouvelles) en 6 rubriques — plats, entrées et salades, soupes,
  apéritif, petit-déjeuner, desserts et goûter. Chacune a un pictogramme, son temps et **ses étapes de
  préparation** (Marmiton devient un simple complément). Filtres en puces : Végétarien (57 recettes), Moins de
  20 min, et chaque rubrique. 60 nouveaux ingrédients ; 4 catégories ajoutées à la base (pois chiches, quinoa,
  chapelure, cacao en poudre) pour les trouver en magasin.
- **Correction de la 3.17** : l'indicateur « ingrédients mal lus », calculé sur l'export d'Open Food Facts, n'était
  pas fiable (œufs frais, yaourts nature… passaient « À vérifier », environ 4 000 produits par allergène). Il n'est
  plus utilisé que d'après la fiche en direct, où Open Food Facts donne le nombre d'ingrédients inconnus. Restent
  actifs sur la base : liste « à compléter » (600 à 1 200 produits par allergène) et allergène repéré par Open Food
  Facts mais non déclaré (50 à 300 produits par allergène).
- Tests : `tests/recettes.py` (catalogue, filtres, préparation).

### 2026-10-19 · 3.17
- **Fiches produit plus fiables.** Pourquoi des produits sortaient « Compatible » à tort : la fiche Open Food Facts
  est incomplète (allergène non déclaré, liste d'ingrédients partielle, mal lue ou dans une autre langue) et la base
  de l'appli date de la semaine. Désormais :
  - à l'ouverture d'une fiche, l'appli recharge la version actuelle d'Open Food Facts et recalcule le verdict
    (fiche, liste de résultats, Ma liste) ; un message prévient si le verdict change ;
  - un allergène repéré par Open Food Facts dans les ingrédients mais non déclaré passe le produit « À vérifier » ;
  - une liste d'ingrédients « à compléter » ou mal lue (plus de la moitié des ingrédients non reconnus) aussi ;
  - **« Une erreur ? Ce produit contient un de mes allergènes »** : l'utilisateur signale le produit, qui devient
    « Exclu » pour lui partout, avec un lien pour corriger la fiche Open Food Facts ;
  - la fiche dit d'où viennent les infos et de quand, et rappelle que « aucun allergène déclaré » ne garantit rien.
- Base de l'appli : listes d'ingrédients gardées jusqu'à 6 000 caractères (2 500 avant), et nouvelles colonnes
  (fiabilité, date de la fiche, allergènes repérés). À mesurer après la prochaine construction : combien de
  produits passent « À vérifier ».
- Tests : `tests/fiches.py` ; sauvegarde (signalements) et robustesse complétées.

### 2026-10-19 · 3.16
- **Résultats plus lisibles** : un résumé d'une ligne (« 4 660 produits analysés · 3 285 vus dans tes magasins »),
  plus de doublons au-dessus de la liste (ligne « près de moi » et bouton du rayon retirés des résultats), plus de
  phrase « Rien de ce que tu évites… » répétée sur chaque produit compatible.
- **Fiches qu'on ferme en les glissant vers le bas** (poignée et titre), comme sur iPhone.
- Cartes grises pendant le chargement, passage animé entre l'accueil et les résultats, pastille de « Ma liste » qui
  rebondit à chaque ajout, puces qui réagissent au toucher.

### 2026-10-19 (3e séance) · 3.15
- **Nouvel accueil.** L'écran Rechercher s'ouvre sur « Que veux-tu acheter ? » et 15 grandes tuiles avec un
  pictogramme : les rayons les plus courants (pain, biscuits, céréales, yaourts, fromages, laits végétaux, pâtes,
  plats préparés, charcuterie, chocolat, gâteaux, apéritif, glaces, desserts, pizzas), puis « Voir tous les
  rayons ». Une tuile = les produits du rayon triés selon les allergies.
- Les résultats ont leur propre en-tête (« ‹ Rayons » et le nom du rayon) ; le geste retour, ce bouton ou
  l'onglet Rechercher ramènent aux tuiles. Le dernier rayon est marqué, et une recherche par nom peut être reprise.
- Un nom tapé depuis l'accueil cherche dans tous les rayons ; sans nom, un message explique quoi faire.
- « Comment ça marche » réécrit : les 3 étapes, les couleurs des verdicts et un bouton pour scanner en magasin.
- Au démarrage, l'appli ouvre toujours l'accueil (avant : les derniers résultats).

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
