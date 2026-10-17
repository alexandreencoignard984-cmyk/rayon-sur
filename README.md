# Rayon sûr

Appli web pour trouver, rayon par rayon, les produits compatibles avec tes allergies (lactose, gluten, fruits à coque…), scanner un code-barres en magasin et garder une liste de courses.

Ouvrir l'appli : https://alexandreencoignard984-cmyk.github.io/rayon-sur/

## Données

- **Base de l'appli** (`data/`) : chaque lundi, la tâche GitHub « Base produits » télécharge l'export complet d'[Open Food Facts](https://fr.openfoodfacts.org), garde les produits vendus en France et les range par rayon (`tools/build_data.py`, rayons et enseignes dans `tools/config.json`). Parcourir un rayon ne dépend donc pas des serveurs de recherche d'Open Food Facts, souvent saturés. La tâche peut aussi être lancée à la main depuis l'onglet Actions.
- **Open Food Facts en direct** : scan d'un code-barres et recherche par nom dans tous les rayons. L'appli réessaie toute seule quand le serveur refuse une requête.
- **Magasins** (`data/stores/`) : chaque lundi, la tâche « Base magasins » récupère sur [OpenStreetMap](https://www.openstreetmap.org) (extraits [Geofabrik](https://download.geofabrik.de), sinon l'API Overpass) les magasins des enseignes connues de l'appli, partout en France (`tools/build_stores.py`), avec adresse, horaires et site web. L'appli en déduit les magasins proches de l'utilisateur sans dépendre des serveurs de cartes ; si cette base est indisponible, elle interroge Overpass en direct. Données © les contributeurs d'OpenStreetMap, licence [ODbL](https://opendatacommons.org/licenses/odbl/).
- **Position** : GPS du téléphone, ou adresse, ville et code postal via la [Base Adresse Nationale](https://adresse.data.gouv.fr) et [geo.api.gouv.fr](https://geo.api.gouv.fr). L'adresse enregistrée sert aussi quand le GPS ne répond pas. La position n'est enregistrée que sur le téléphone.
- **Stock au drive** : les stocks ne sont pas publics ; l'appli ouvre le site de l'enseigne (sa propre recherche) sur le produit, et le site affiche la disponibilité dans le drive choisi.
- **[RappelConso](https://rappel.conso.gouv.fr)** : rappels officiels, vérifiés sur chaque fiche.
- **[Open Prices](https://prices.openfoodfacts.org)** : prix relevés en magasin.

Licences ouvertes. L'étiquette du produit fait toujours foi.
