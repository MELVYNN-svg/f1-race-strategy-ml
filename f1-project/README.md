# Projet F1 avec Kedro

Ce projet utilise FastF1 pour importer les données et Kedro pour les préparer et les charger. Les fichiers déjà installés suffisent pour travailler hors ligne.

**Pour savoir comment appeler chaque donnée, choisir un GP, une session et un pilote, consultez le [guide d'accès aux données F1](GUIDE_ACCES_DONNEES_F1.md).**

**Archive 2024–2025 :** [diagnostic initial du 2 novembre 2026](docs/AUDIT_INITIAL_FASTF1_2024_2025.md)
et [collecte, reprise, statuts, unités et restauration](docs/FASTF1_ARCHIVE_OPERATIONS.md).
Le pipeline `data_quality` lit réellement les fichiers et publie `fastf1_coverage`
et `fastf1_quality`. La présence d'un fichier seule ne vaut jamais COMPLETE.

## Commencer avec les données présentes

Depuis la racine du projet dans PowerShell :

```powershell
conda activate verstappen
kedro run
kedro jupyter lab
```

Le projet utilise l'environnement Conda existant **`verstappen`**.

Le [guide d'accès aux données F1](GUIDE_ACCES_DONNEES_F1.md) contient les appels du catalogue et des exemples à copier dans votre notebook.

Dans un notebook :

```python
%load_ext kedro.ipython

laps = catalog.load("fastf1_laps")
results = catalog.load("fastf1_results")
weather = catalog.load("fastf1_weather")
sessions = catalog.load("fastf1_sessions")
```

`kedro run` crée les tables à partir des fichiers locaux. Il ne lance plus de téléchargement. Après un nouvel import, relancez-le pour actualiser ces tables. Si le catalogue était déjà chargé dans un notebook avant la mise à jour, utilisez `%reload_kedro`.

## Sélectionner une course et un pilote

Les tables de saison ajoutent cinq colonnes de contexte : `year`, `event_code`, `round_number`, `session_code`, `session_name`. Les colonnes originales FastF1 restent présentes.

```python
# Tous les tours de course du GP d'Australie, puis ceux de Verstappen.
australia = laps.query("round_number == 1 and session_name == 'race'")
verstappen = australia.loc[australia["Driver"].eq("VER")].copy()
verstappen["lap_time_seconds"] = verstappen["LapTime"].dt.total_seconds()
verstappen[["Driver", "LapNumber", "Compound", "lap_time_seconds"]].head()
```

`LapTime`, `Sector1Time`, etc. restent des durées pandas. `IsPersonalBest` est un booléen nullable dans les tables préparées. Dans `race_control`, `Lap` et `Sector` sont des entiers nullables. Les dates de session des fiches d'événement sont harmonisées en UTC.

## Ce que le catalogue expose

| Nom | Contenu |
| --- | --- |
| `fastf1_schedule` | Calendrier brut de la saison |
| `fastf1_events` | Fiches des événements |
| `fastf1_laps` | Tours, chronos, pneus, secteurs |
| `fastf1_results` | Classements par session |
| `fastf1_weather` | Météo par session |
| `fastf1_stints` | Relais et pneumatiques |
| `fastf1_pit_events` | Tours avec une entrée ou sortie des stands |
| `fastf1_track_status` | État de piste |
| `fastf1_session_status` | État des sessions |
| `fastf1_race_control` | Messages de direction de course |
| `fastf1_circuit_corners` | Virages et coordonnées |
| `fastf1_circuit_marshal_lights` | Positions des feux des commissaires |
| `fastf1_circuit_marshal_sectors` | Secteurs des commissaires |
| `fastf1_circuit_rotation` | Rotation du tracé |
| `fastf1_inventory` | Un enregistrement par fichier brut reconnu, sans lire la télémétrie |
| `fastf1_sessions` | Sessions attendues et présence des fichiers locaux |
| `fastf1_ingestion_report` | Rapport du dernier import terminé, potentiellement plus ancien que les fichiers |
| `fastf1_raw` | Dictionnaire de partitions brutes chargées à la demande |
| `openf1_meetings`, `openf1_sessions` | Calendriers OpenF1 locaux, distincts des tables FastF1 |

Les tables de saison contiennent seulement les fichiers disponibles. Une session absente n'est pas reconstituée et les essais hivernaux portent `round_number == 0`.

```python
sessions.loc[sessions["has_laps"], ["event_code", "event_name", "session_code"]]
# Sessions dont les tours ne sont pas encore présents :
sessions.loc[~sessions["has_laps"], ["event_name", "session_name"]]
```

`has_laps` / `has_results` indiquent la présence d'un fichier ; ils ne garantissent pas que toutes ses lignes sont complètes. `car_data_files` / `position_files` comptent les fichiers pilotes.

## Télémétrie et accès direct sans préparation

La télémétrie reste séparée par pilote pour éviter de charger des dizaines de millions de lignes. Les modèles du catalogue permettent de charger directement un fichier, même avant `kedro run` :

```python
# Une table d'une session : événement, dossier de session, table.
laps_australia = catalog.load("fastf1_table__round_01__05_race__laps")

# Un pilote : événement, dossier de session, car_data/position, numéro.
telemetry = catalog.load("fastf1_driver__round_01__05_race__car_data__1")
position = catalog.load("fastf1_driver__round_01__05_race__position__1")

# OpenF1 : clé de session, table. La session 9683 est présente localement.
openf1_laps = catalog.load("openf1_table__9683__laps")
```

Reprenez `session_code` depuis `fastf1_sessions` : l'ordre varie lors des week-ends sprint. Par exemple, `03_sprint` et `04_qualifying` sont distincts. Les accès directs renvoient les colonnes brutes, sans les cinq colonnes ajoutées par la préparation. Un fichier absent produit une erreur explicite.

Pour explorer les fichiers bruts sans les charger tous :

```python
partitions = catalog.load("fastf1_raw")
keys = sorted(key for key in partitions if key.endswith("/laps"))
raw_laps = partitions[keys[0]]()  # Les parenthèses lisent ce fichier seulement.
```

## Disposition des données

```text
data/
  00_cache/fastf1/                     cache de téléchargement FastF1
  01_raw/fastf1/2025/                  exports bruts existants
    schedule.parquet
    round_01/
      event.parquet
      05_race/
        laps.parquet, results.parquet, weather.parquet, ...
        car_data/1.parquet, ...
        position/1.parquet, ...
    test_01/...
  01_raw/openf1/2025/                  source OpenF1 distincte
  03_primary/fastf1/2025/              13 tables de saison prêtes à analyser
  08_reporting/2025/                  inventaire, disponibilité, rapports d'import
```

La disposition brute est conservée. Les tables préparées sont de petits fichiers dérivés, régénérables ; la télémétrie n'est pas dupliquée dans `03_primary`. Les autres niveaux Kedro restent disponibles pour les futures variables, modèles et prédictions.

## Importer ou changer de saison

L'import réseau est explicite et peut être long :

```powershell
kedro run --pipeline data_ingestion
kedro run --pipeline data_preparation
```

L'import compare les exports au contenu FastF1, conserve les fichiers identiques
et sauvegarde les originaux avant une réparation. Les sessions déjà comparées
sont ignorées seulement si leurs preuves et empreintes restent valides. Vérifiez
`fastf1_coverage` et `fastf1_quality` après collecte. Pour les deux saisons avec
attente automatique du limiteur, utilisez le CLI décrit dans le guide d'exploitation.

L'année par défaut se règle dans `conf/base/globals.yml`. La même surcharge est utilisée pour les paramètres et tous les chemins du catalogue :

```powershell
kedro run --params year=2024
# Pour télécharger d'abord une autre saison :
kedro run --pipeline data_ingestion --params year=2024
kedro run --pipeline data_preparation --params year=2024
```

Une préparation requiert les fichiers bruts et le calendrier de cette saison. Dans un notebook, `%reload_kedro --params year=2024` sélectionne les mêmes chemins.

## Installation et vérification

Pour une nouvelle installation :

```powershell
conda activate verstappen
python -m pip install -e ".[dev]"
python -m pytest
```

`requirements.txt` permet aussi une installation avec `python -m pip install -r requirements.txt`. Les dépendances FastF1 et Parquet sont déclarées. Les tests utilisent des données temporaires et ne téléchargent pas de saison.

Les données, le cache et la configuration locale sont exclus de Git. Conservez les identifiants éventuels dans `conf/local/`.

Les accès ciblés utilisent les [dataset factories de Kedro](https://docs.kedro.org/en/stable/catalog-data/kedro_dataset_factories/) et les fichiers bruts utilisent son [chargement par partitions](https://docs.kedro.org/en/1.5.0/catalog-data/partitioned_and_incremental_datasets/).
