# Rayon sûr

Appli web pour trouver, rayon par rayon, les produits compatibles avec tes allergies (lactose, gluten, fruits à coque…), scanner un code-barres en magasin et garder une liste de courses.

Ouvrir l'appli : https://alexandreencoignard984-cmyk.github.io/rayon-sur/

## Données

- **Base de l'appli** (`data/`) : chaque lundi, la tâche GitHub « Base produits » télécharge l'export complet d'[Open Food Facts](https://fr.openfoodfacts.org), garde les produits vendus en France et les range par rayon (`tools/build_data.py`, rayons et enseignes dans `tools/config.json`). Parcourir un rayon ne dépend donc pas des serveurs de recherche d'Open Food Facts, souvent saturés. La tâche peut aussi être lancée à la main depuis l'onglet Actions.
- **Open Food Facts en direct** : scan d'un code-barres et recherche par nom dans tous les rayons. L'appli réessaie toute seule quand le serveur refuse une requête.
- **[RappelConso](https://rappel.conso.gouv.fr)** : rappels officiels, vérifiés sur chaque fiche.
- **[Open Prices](https://prices.openfoodfacts.org)** : prix relevés en magasin.

Licences ouvertes. L'étiquette du produit fait toujours foi.
