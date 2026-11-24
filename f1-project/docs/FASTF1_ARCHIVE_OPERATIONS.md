# Archive FastF1 2024–2025 : exploitation et limites

## Exécution

Depuis la racine, dans l'environnement Conda existant :

```powershell
conda activate verstappen
$env:PYTHONPATH = (Resolve-Path src).Path
python -m f1_project.fastf1_cli --years 2025 2024 --ingest --wait-rate-limit
```

Le calendrier est obtenu par `fastf1.get_event_schedule(include_testing=True)`.
Les sessions sont celles des champs Session1…Session5 ; les essais utilisent
`fastf1.get_testing_session`, les autres `fastf1.get_session`. Aucun appel direct
à une autre API sportive. Les dépendances internes de FastF1 restent gérées par
FastF1. Les anciennes données OpenF1 ne participent à aucun traitement.

Depuis octobre 2026, l'accès à la plupart des données non mises en cache nécessite
une authentification F1TV Access/Pro/Premium, selon les
[notes officielles FastF1 3.9](https://github.com/theOehrly/Fast-F1/releases/tag/v3.9.0).
La connexion se fait localement, sans mettre d'identifiants dans le dépôt :

```powershell
python -m fastf1 auth f1tv --authenticate
python -m fastf1 auth f1tv --status
```

Ne pas confondre `SessionNotAvailableError` en mode non authentifié avec une
absence historique certaine. Les exceptions internes absorbées par FastF1 sont
conservées dans `source_diagnostics` des manifestes. Les propriétés accessibles
(par exemple les résultats) sont exportées même si d'autres ne sont pas chargées.
Après connexion, `--retry-unavailable` permet de revérifier les constats
SOURCE_UNAVAILABLE tout en conservant les points de reprise des sessions complètes.

Une seule session est chargée en mémoire. Les fichiers voiture/position restent
partitionnés par pilote. Le verrou exclusif empêche deux exécutions du CLI de
modifier simultanément l'archive. Ne lancer aucun autre import Kedro en parallèle.
Le CLI termine chaque saison par son audit et sa préparation locale, en réutilisant
les mêmes fonctions que les pipelines Kedro. `status=FINISHED` signifie que le
traitement est terminé ; seul `outcome=COMPLETE` signifie que tous les datasets
attendus sont complets ou non applicables. `outcome=PARTIAL` conserve les lacunes.
Une interruption libère le verrou système ; le fichier ingestion.lock peut rester.

Le délai d'un limiteur déjà déclenché est enregistré dans `network_cooldown.json`
et conservé lors du redémarrage du CLI. Chaque session en échec non lié au limiteur
n'est tentée qu'une fois par passage complet, en plus des tentatives bornées
internes : une erreur permanente ne bloque plus l'avancement de toute la saison.

La limite FastF1 provoque un arrêt propre du lot, puis une attente de 3605 secondes
si `--wait-rate-limit` est utilisé. Aucun limiteur n'est désactivé. Les autres
exceptions font l'objet de trois tentatives espacées de 2 et 4 secondes.
FastF1 peut absorber des erreurs internes : consulter aussi les messages de
chargement et les datasets ERROR, pas seulement le code de sortie du programme.

Relancer la même commande reprend les sessions sans preuve valide. Les sessions
validées et dont les empreintes sont inchangées ne sont pas rechargées. `--refresh`
recompare également ces sessions ; il réutilise le cache et ne force pas son
effacement. `--max-sessions N` limite un lot aux N sessions à revérifier.
Ne pas associer une petite limite de lot à l'attente automatique d'un ancien
rate-limit sans vérifier les journaux. Aucun mécanisme ne transforme une fin de
processus en déclaration d'exhaustivité de la source.

Audit local sans téléchargement :

```powershell
python -m f1_project.fastf1_cli --years 2025 2024
kedro run --pipeline data_quality --params year=2025
kedro run --pipeline data_preparation --params year=2025
kedro run --pipeline data_preparation --params year=2024
```

## Statuts

| Statut | Sens |
| --- | --- |
| COMPLETE | Export non vide comparé intégralement au retour FastF1 ; empreinte vérifiée et structure minimale valide. Ne prouve pas que le fournisseur a capturé toute la réalité sportive. |
| PARTIAL | Ancien export non encore comparé, empreinte modifiée, table vide, anomalie structurelle ou régression de source conservée pour examen. |
| MISSING | Fichier attendu absent, sans preuve de disponibilité fournie par une collecte. |
| SOURCE_UNAVAILABLE | Objet vide retourné par FastF1 ou pilote actif absent du dictionnaire de télémétrie chargé. Constat de cette exécution, pas preuve d'une indisponibilité définitive. |
| NOT_APPLICABLE | Table dérivée sans occurrence (par exemple aucun passage aux stands). |
| ERROR | Échec de lecture, d'écriture ou d'accès à une propriété/à une session. |

Les pilotes actifs viennent des tours et des dictionnaires FastF1. On n'impose
pas vingt pilotes ni le nombre de tours du vainqueur aux pilotes ayant abandonné.
Les contrôles de course comparent le maximum de tours de chaque pilote à son
propre champ Laps dans les résultats. Une session sans information pilotes reste
une lacune au niveau session ; aucun numéro de pilote n'est inventé.

Les indicateurs historiques `has_laps` et `has_results` restent des indicateurs de
présence. Utiliser `fastf1_coverage`, les manifestes et la qualité pour l'audit.

## Fichiers d'évidence et restauration

- `data/08_reporting/mission_2024_2025/initial_inventory.json` : mesure initiale.
- `data/08_reporting/mission_2024_2025/run_state.json` : phase, PID et état du CLI.
- `data/08_reporting/<année>/manifests/*.json` : résultats source, schémas,
  nombres de lignes, empreintes SHA-256, diagnostics, dates UTC et version FastF1.
- `fastf1_recovery.jsonl` : historique des collectes de sessions.
- `fastf1_coverage.parquet` et `.csv` : couverture par dataset/session/pilote.
- `fastf1_quality.parquet` et `.csv` : anomalies, gravité, effectifs et explications.
- `fastf1_session_coverage.parquet` : agrégation des statuts par session.
- `fastf1_driver_coverage.parquet` et `.csv` : identité, participation observée,
  tours/résultats/télémétrie par pilote et session, sans affectation d'équipe annuelle.
- `fastf1_event_coverage.parquet` : concordance des fiches événement avec le calendrier.
- `fastf1_schemas.parquet` : variantes de schéma observées par dataset et année.

Avant remplacement d'un original, celui-ci est copié sous
`data/00_backup/fastf1/<année>/<chemin>.<sha256>.bak` et son empreinte est comparée.
Le candidat Parquet est entièrement relu avant remplacement atomique. Les
fichiers identiques conservent leurs octets et leur date de modification. Une
source retournant moins de lignes ou moins de colonnes ne remplace pas
automatiquement un original plus riche : statut PARTIAL et original préservé.

Pour restaurer, conserver d'abord une copie du fichier courant, puis recopier la
sauvegarde `.bak` au chemin source indiqué dans le manifeste. Le prochain audit
détectera son empreinte différente et demandera une nouvelle comparaison.
Ne jamais renommer les sauvegardes `.bak` en `.parquet` dans l'arbre des bruts :
elles seraient prises pour des partitions sportives par Kedro.

## Données nouvelles

`session_info` préserve les champs publics imbriqués sous forme de colonnes
aplaties ; `session_metadata` conserve `t0_date`, `session_start_time`, `total_laps`,
la date, le nom et le support de l'API ; `drivers` conserve les numéros publics.
Les méthodes d'enrichissement télémétrique (distance intégrée, voiture devant,
rééchantillonnage) ne sont pas des mesures indépendantes et ne sont pas ajoutées
silencieusement aux bruts.

`pit_events` conserve sa définition historique. `pit_stops` apparie chaque entrée
avec la sortie suivante ; les entrées/sorties sans paire restent présentes.
`lane_elapsed` est une estimation par différence de deux temps, pas une durée
d'immobilisation. Un long intervalle peut inclure un arrêt au garage ou un drapeau
rouge. Le contexte est obtenu des états de piste sur tout l'intervalle. Les
composés proviennent des tours associés aux événements et peuvent être ambigus
quand l'entrée et la sortie appartiennent à la même ligne de tour.

Les relais ajoutent la séquence de composés observés, le nombre de tours chronométrés,
la somme des chronos disponibles et l'intervalle premier départ/dernière fin.
Ces deux durées n'ont pas la même définition. Les valeurs inconnues et les composés
d'essais sont conservés. SOFT/MEDIUM/HARD sont des choix relatifs au week-end,
sans correspondance physique universelle C1/C2/etc. ajoutée.

## Unités, temps et limites scientifiques

| Champ | Unité / interprétation |
| --- | --- |
| LapTime, secteurs, Time, SessionTime, PitInTime, PitOutTime | Durées pandas ; `.dt.total_seconds()` pour des secondes |
| Date, LapStartDate, t0_date | Horloge UTC ; exports bruts conservés, dates préparées explicitement en UTC |
| Speed, SpeedI1, SpeedI2, SpeedFL, SpeedST | km/h |
| RPM | tours/minute |
| Throttle | Pourcentage ; 104 est documenté comme code d'erreur/indisponibilité, conservé et signalé |
| Brake | Booléen, pas pression de freinage |
| X/Y/Z | Dixième de mètre (2024–2025), pas mètres |
| AirTemp, TrackTemp | °C ; aucune température interne du pneu |
| Pressure | Pression atmosphérique en mbar ; aucune pression de pneu |
| WindSpeed / WindDirection | m/s / degrés |
| Humidity | % |
| TyreLife | Âge du train en tours, pas durée de vie restante |
| DRS / TrackStatus | Codes source conservés ; ne pas convertir en booléens sans définition |

Les zéros, tours lents, interruptions et mesures avant départ restent présents.
`FastF1Generated`, `Deleted`, `DeletedReason` et `IsAccurate` sont conservés.
Les contrôles REVIEW demandent un examen contextualisé ; INVALID désigne une
structure/type impossible ou une durée négative. Aucune suppression ni correction
numérique automatique n'est effectuée. Les nulls sont comptés par colonne.

Les trous de plus de dix secondes en télémétrie incluent les périodes légitimes
d'inactivité. Les flux voiture et position ne sont pas synchrones : l'audit mesure
la distance temporelle au véritable échantillon voisin, sans interpolation.
Il ne promet pas un alignement exact ni une cadence uniforme.

Références : documentation intégrée dans la version FastF1 3.9.0 installée
(`core.Session`, `core.Telemetry`, `_api.position_data`, `_api.weather_data`),
et [code officiel FastF1](https://github.com/theOehrly/Fast-F1/blob/main/fastf1/_api.py).
La consultation de `_api.py` sert à documenter les unités ; la collecte n'appelle
aucune fonction privée.

## Tests

Les fixtures sont synthétiques, sans performance historique fabriquée :

```powershell
python -m pytest -q --basetemp=tmp/pytest-local-new
python -m ruff check src tests
python -m ruff format --check src tests
```

Choisir un nouveau dossier temporaire de test afin de ne pas réutiliser un dossier
contenant d'autres travaux. Les dépendances de test sont déclarées dans l'extra dev.
