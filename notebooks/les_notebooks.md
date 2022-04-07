## Quelques notebooks pour mieux comprendre les annotateurs "annotateurTox"

### 22-04_install_quickumls_tox_dict

Pour extraire les toxicités, j'ai utilisé QuickUMLS sur un dictionnaires de termes. J'ai regroupé les termes trouvés dans différentes sources de toxicité et ai créé des fichiers MRCONSO et MRSTY, nécessaires pour utiliser QuickUMLS. Ce notebook explique l'installation.

### 22-04_Stanza_get_started

Un notebook très brouillon, pour comprendre les annotations et le parser de dépendance de Stanza.
Il permettra peut-être de mieux comprendre l'annotateur pymedext "stanzaAnnotator" (qui a d'ailleurs été plus commenté).
Des visualisations brat sont générables

### Notebook 22-04_relations_between_entities

Ce notebook reprend l'extraction d'entités d'intérêt, et montre comment j'ai fait pu faire le lien entre elles grâce aux relations Pymedext.
Des visualisations brat sont générables.


### Fichier de configuration

! Penser à modifier le ficier de configuration !
Il faut notamment modifier le chemin vers les données QuickUMLS dès qu'elles auront été générées, ainsi que les chemins vers les dossiers brats.


