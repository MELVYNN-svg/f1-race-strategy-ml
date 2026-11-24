# Bilan provisoire — 2 novembre 2026, 11 h 43 (Paris)

**Implémentation et vérification locale : effectuées. Ingestion des deux saisons :
PARTIAL, encore en cours. Ce document n'est pas une attestation d'exhaustivité.**

| Mesure sur disque | Avant travaux | À ce point de contrôle |
| --- | ---: | ---: |
| Parquet bruts 2025 | 5682 | 6118 |
| Sessions 2025 avec tours | 109 / 123 | 109 / 123 |
| Sessions 2025 dont tous les exports du manifeste sont COMPLETE | aucune preuve | 109 |
| Exports session/pilote comparés à FastF1 et COMPLETE | aucune preuve | 6092 |
| Courses 2025 avec tours | manches 1–21 | manches 1–21 |
| Parquet bruts 2024 | 0 | 1 (calendrier uniquement) |

Le total 6118 inclut 25 fiches événement et le calendrier, en plus des 6092
exports de sessions/pilotes. Les nouvelles données sont surtout des métadonnées,
des listes de pilotes et des passages aux stands dérivés. Ne pas interpréter
l'augmentation du nombre de fichiers comme 436 sessions nouvellement récupérées.
Le calendrier 2024 issu du cache FastF1 a été publié : 25 événements et 123
sessions attendues. Son audit initial compte 2214 unités dataset/session MISSING ;
ces unités incluent les emplacements de télémétrie dont les pilotes restent à
déterminer. Ce nombre ne représente ni 2214 pilotes ni 2214 sessions.

157 originaux (1367824 octets) ont été conservés dans les sauvegardes adressées
par SHA-256. Les fichiers identiques n'ont pas été remplacés. Les données OpenF1
existantes n'ont été ni utilisées ni modifiées.

## Ce qui a été livré

- Collecte via les interfaces FastF1 publiques uniquement, avec calendrier réel,
  essais, sessions sprint et télémétrie par pilote.
- Comparaison du contenu source, preuves persistantes par dataset, sommes SHA-256,
  sauvegardes vérifiées, écritures atomiques et reprise.
- Protection contre les régressions de source, reprises réseau bornées, délai de
  limiteur conservé lors d'un redémarrage et absence de boucle sur les échecs fixes.
- Export des métadonnées, origines temporelles, pilotes, relais enrichis et
  passages aux stands appariés. Durée aux stands explicitement estimée.
- Audit de contenu, schémas, nulls, chronologie, unités, doublons, secteurs,
  identités pilotes/équipes, relais, canaux et alignement voiture/position.
- Couverture par événement/session/pilote/dataset avec les six statuts demandés.
- Catalogue Kedro étendu, pipeline data_quality, préparation automatique en fin
  de collecte de chaque saison, guide et documentation de restauration.

## Vérifications et constats

39 tests hors ligne passent. Contrôles Ruff et compilation Python passent.
La préparation Kedro 2025 et sa variante à publication atomique ont réussi.
Les 25 fiches événement concordent avec le calendrier après normalisation des
fuseaux pour comparaison, sans modification des dates sources.

L'audit scientifique des données disponibles a trouvé 110 lignes dupliquées,
66 écarts secteur/tour dépassant 5 ms, 532 intervalles de télémétrie supérieurs
à 10 secondes et 4326 valeurs de canaux à examiner. Ces effectifs sont des
signalements, pas une preuve d'observations invalides. Les 13009112 valeurs
Throttle=104 sont séparées comme code d'indisponibilité documenté par FastF1.
Aucune de ces observations n'a été supprimée ou interpolée.

## Blocage et reprise active

FastF1 3.9 requiert une authentification F1TV active pour les données non présentes
dans le cache ou disponibles sur son serveur de repli. Les sessions manquantes de
fin 2025 ont renvoyé SessionNotAvailableError en mode non authentifié. Le premier
lot répétait ces erreurs jusqu'au limiteur ; cette boucle a été arrêtée et corrigée.

La reprise corrigée traite 2024 puis 2025. Elle conserve le délai déjà déclenché
jusqu'au **2 novembre 2026 à 12:02:57,785 heure de Paris**, puis attend une
authentification locale valide si elle n'a pas encore été faite. Le contrôle
utilise uniquement `python -m fastf1 auth f1tv --status`, sans lecture ni affichage
du jeton. Le processus reprend automatiquement après ces deux conditions.

Le PID et l'état présent doivent être relus dans
`data/08_reporting/mission_2024_2025/run_state.json` ; ce document est un instantané.
Le journal actif est `recovery_authenticated.log` dans le même dossier.
Le CLI publiera les audits et tables préparées de chaque saison. Une fin normale
du processus n'est pas une promesse de données complètes : consulter `outcome`
et `year_outcomes`, ainsi que les rapports de couverture.

Connexion à réaliser par l'utilisateur dans son terminal :

```powershell
& "C:\Users\melvy\miniconda3\envs\verstappen\python.exe" -m fastf1 auth f1tv --authenticate
& "C:\Users\melvy\miniconda3\envs\verstappen\python.exe" -m fastf1 auth f1tv --status
```

Références d'accès : [authentification officielle FastF1](https://github.com/theOehrly/Fast-F1/blob/main/docs/api_reference/accounts_auth.rst)
et [notes de version 3.9.0](https://github.com/theOehrly/Fast-F1/releases/tag/v3.9.0).
Le texte de mission reçu s'arrête au milieu de la section 5.
