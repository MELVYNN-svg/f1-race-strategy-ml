# Comment charger et choisir les données F1 avec Kedro

Ce guide explique **quoi écrire dans un notebook**, ce que chaque appel renvoie,
et comment savoir de quelle course, de quelle session et de quel pilote viennent
les données. Les exemples correspondent au catalogue de ce projet et ont été
vérifiés sur les fichiers locaux le **24 octobre 2026**.

## Fiche à consulter d'abord : numéros, pilotes et écuries

Cette fiche te donne les correspondances directement, sans avoir à écrire du
code pour les découvrir. Elle concerne **la saison 2025 chargée dans le projet**.
Les résultats détaillés locaux couvrent actuellement les manches 1 à 13, jusqu'au
GP de Belgique, ainsi que les essais hivernaux. Les listes ci-dessous regroupent
**tous les 32 numéros présents dans ces résultats**, y compris les pilotes
apparus uniquement en essais libres. Elles ne décrivent pas la grille 2026.

### Pilotes présents dans les résultats de course

Le numéro de la première colonne est celui à mettre **à la fin de l'appel
`fastf1_driver__...`**. L'abréviation est celle à utiliser dans les filtres
`laps["Driver"]` ou `results["Abbreviation"]`.

| Numéro | Abréviation | Pilote | Écurie observée dans tes courses 2025 |
| --- | --- | --- | --- |
| `1` | `VER` | Max Verstappen | Red Bull Racing |
| `4` | `NOR` | Lando Norris | McLaren |
| `5` | `BOR` | Gabriel Bortoleto | Kick Sauber |
| `6` | `HAD` | Isack Hadjar | Racing Bulls |
| `7` | `DOO` | Jack Doohan | Alpine — manches 1 à 6 |
| `10` | `GAS` | Pierre Gasly | Alpine |
| `12` | `ANT` | Andrea Kimi Antonelli | Mercedes |
| `14` | `ALO` | Fernando Alonso | Aston Martin |
| `16` | `LEC` | Charles Leclerc | Ferrari |
| `18` | `STR` | Lance Stroll | Aston Martin |
| `22` | `TSU` | Yuki Tsunoda | Racing Bulls aux manches 1–2 ; Red Bull Racing aux manches 3–13 |
| `23` | `ALB` | Alexander Albon | Williams |
| `27` | `HUL` | Nico Hulkenberg | Kick Sauber |
| `30` | `LAW` | Liam Lawson | Red Bull Racing aux manches 1–2 ; Racing Bulls aux manches 3–13 |
| `31` | `OCO` | Esteban Ocon | Haas F1 Team |
| `43` | `COL` | Franco Colapinto | Alpine — manches 7 à 13 |
| `44` | `HAM` | Lewis Hamilton | Ferrari |
| `55` | `SAI` | Carlos Sainz | Williams |
| `63` | `RUS` | George Russell | Mercedes |
| `81` | `PIA` | Oscar Piastri | McLaren |
| `87` | `BEA` | Oliver Bearman | Haas F1 Team |

Dans certains fichiers, Antonelli est nommé `Andrea Kimi Antonelli`, et dans
d'autres `Kimi Antonelli`. C'est le même pilote : numéro `12`, abréviation `ANT`.
Une ligne dans cette liste ne garantit pas un fichier de télémétrie pour toutes
les sessions ; il faut vérifier la session et le fichier voulu.

### Changements importants pour ton étude Red Bull

| Courses de tes données | Red Bull Racing | Racing Bulls | Alpine |
| --- | --- | --- | --- |
| Australie et Chine — manches 1–2 | Verstappen `1` + Lawson `30` | Tsunoda `22` + Hadjar `6` | Gasly `10` + Doohan `7` |
| Japon à Miami — manches 3–6 | Verstappen `1` + Tsunoda `22` | Lawson `30` + Hadjar `6` | Gasly `10` + Doohan `7` |
| Émilie-Romagne à Belgique — manches 7–13 | Verstappen `1` + Tsunoda `22` | Lawson `30` + Hadjar `6` | Gasly `10` + Colapinto `43` |

**Ne considère donc pas `22` ou `30` comme un identifiant permanent de
l'écurie Red Bull.** Le numéro identifie le pilote dans le contexte de la
session ; l'écurie se lit dans `Team` ou `TeamName`. Pour étudier toute l'équipe,
filtre sur `Red Bull Racing` plutôt que de fixer une seule paire de numéros
pour toute la saison.

Exemples concrets :

| Appel au catalogue | Voiture identifiée |
| --- | --- |
| `fastf1_driver__round_01__05_race__car_data__1` | Verstappen, Red Bull, course d'Australie |
| `fastf1_driver__round_01__05_race__car_data__30` | Lawson, Red Bull, course d'Australie |
| `fastf1_driver__round_01__05_race__car_data__22` | Tsunoda, Racing Bulls, course d'Australie |
| `fastf1_driver__round_03__05_race__car_data__22` | Tsunoda, Red Bull, course du Japon |
| `fastf1_driver__round_03__05_race__car_data__30` | Lawson, Racing Bulls, course du Japon |

### Autres pilotes et numéros : apparitions en essais libres

Ces entrées sont présentes dans tes résultats de **première séance d'essais
libres (`01_practice_1`)**. Leur présence ne signifie pas qu'ils ont disputé la
course du dimanche. Le numéro peut être spécifique à une apparition en essais.

| Numéro | Abréviation | Pilote | Écurie observée | GP présents dans tes fichiers |
| --- | --- | --- | --- | --- |
| `34` | `DRU` | Felipe Drugovich | Aston Martin | Bahreïn — `round_04` |
| `36` | `LIN` | Arvid Lindblad | Red Bull Racing | Grande-Bretagne — `round_12` |
| `37` | `IWA` | Ayumu Iwasa | Red Bull Racing | Bahreïn — `round_04` |
| `38` | `BEG` | Dino Beganovic | Ferrari | Bahreïn et Autriche — `round_04`, `round_11` |
| `45` | `MAR` | Victor Martins | Williams | Espagne — `round_09` |
| `46` | `BRO` | Luke Browning | Williams | Bahreïn — `round_04` |
| `50` | `HIR` | Ryo Hirakawa | Haas F1 Team | Bahreïn et Espagne — `round_04`, `round_09` |
| `62` | `HIR` | Ryo Hirakawa | Alpine | Japon — `round_03` |
| `72` | `VES` | Frederik Vesti | Mercedes | Bahreïn — `round_04` |
| `89` | `DUN` | Alexander Dunne | McLaren | Autriche — `round_11` |
| `97` | `ARO` | Paul Aron | Kick Sauber | Grande-Bretagne — `round_12` |

**Cas à retenir : `HIR` apparaît avec deux numéros dans tes fichiers**, `62`
chez Alpine et `50` chez Haas. Il faut toujours associer numéro, événement et
session. Pour les essais britanniques de Red Bull, les résultats mentionnent
aussi Lindblad `36` : ne suppose pas que les deux voitures sont toujours
pilotées par les titulaires.

### Noms exacts des écuries à utiliser dans les filtres

| Écurie | Texte exact dans `laps.Team` / `results.TeamName` | Pilotes de course observés, numéros entre parenthèses |
| --- | --- | --- |
| Red Bull | `Red Bull Racing` | VER (1), LAW (30) puis TSU (22) |
| Racing Bulls | `Racing Bulls` | HAD (6), TSU (22) puis LAW (30) |
| McLaren | `McLaren` | NOR (4), PIA (81) |
| Ferrari | `Ferrari` | LEC (16), HAM (44) |
| Mercedes | `Mercedes` | RUS (63), ANT (12) |
| Aston Martin | `Aston Martin` | ALO (14), STR (18) |
| Alpine | `Alpine` | GAS (10), DOO (7) puis COL (43) |
| Williams | `Williams` | ALB (23), SAI (55) |
| Sauber | `Kick Sauber` | HUL (27), BOR (5) |
| Haas | `Haas F1 Team` | OCO (31), BEA (87) |

Les filtres `.eq(...)` utilisent l'orthographe exacte. Par exemple `Red Bull`
ne correspond pas à la valeur enregistrée `Red Bull Racing`.

### Tous les codes de Grand Prix de ton calendrier 2025

La colonne « sessions locales » décrit la présence des fichiers de tours lors
de la vérification du 24 octobre 2026. Un événement avec calendrier seulement
ne permet pas de charger sa télémétrie : les fichiers correspondants manquent.

| Code à mettre dans l'appel | Grand Prix / événement | Sessions locales avec fichier de tours |
| --- | --- | --- |
| `test_01` | Essais hivernaux | 3 |
| `round_01` | Australie | 5 |
| `round_02` | Chine | 5 |
| `round_03` | Japon | 5 |
| `round_04` | Bahreïn | 5 |
| `round_05` | Arabie saoudite | 5 |
| `round_06` | Miami | 5 |
| `round_07` | Émilie-Romagne — Imola | 5 |
| `round_08` | Monaco | 5 |
| `round_09` | Espagne — Barcelone | 5 |
| `round_10` | Canada | 5 |
| `round_11` | Autriche | 5 |
| `round_12` | Grande-Bretagne | 5 |
| `round_13` | Belgique | 5 |
| `round_14` | Hongrie | 0 — calendrier seulement |
| `round_15` | Pays-Bas | 0 — calendrier seulement |
| `round_16` | Italie — Monza | 0 — calendrier seulement |
| `round_17` | Azerbaïdjan | 0 — calendrier seulement |
| `round_18` | Singapour | 0 — calendrier seulement |
| `round_19` | États-Unis — Austin | 0 — calendrier seulement |
| `round_20` | Mexico | 0 — calendrier seulement |
| `round_21` | São Paulo — Brésil | 0 — calendrier seulement |
| `round_22` | Las Vegas | 0 — calendrier seulement |
| `round_23` | Qatar | 0 — calendrier seulement |
| `round_24` | Abu Dhabi | 0 — calendrier seulement |

### Les week-ends sprint présents dans les exports détaillés

La Chine (`round_02`), Miami (`round_06`) et la Belgique (`round_13`) utilisent
les cinq dossiers suivants dans tes fichiers :

| Code de session | Signification |
| --- | --- |
| `01_practice_1` | Essais libres |
| `02_sprint_qualifying` | Qualifications du sprint |
| `03_sprint` | Sprint |
| `04_qualifying` | Qualifications du GP |
| `05_race` | Course principale |

Les autres GP ayant des exports détaillés utilisent les essais libres 1, 2,
3, puis les qualifications et la course. Pour `test_01`, `01_practice_1`,
`02_practice_2`, `03_practice_3` correspondent aux trois journées d'essais.

### Codes d'état de piste utiles à la stratégie

Dans `fastf1_track_status.Status`, les codes présents sont des chaînes de texte :

| Code | Signification |
| --- | --- |
| `"1"` | Piste libre / retour au régime normal |
| `"2"` | Drapeau jaune |
| `"4"` | Safety Car |
| `"5"` | Drapeau rouge |
| `"6"` | Virtual Safety Car déployée |
| `"7"` | Fin annoncée de la Virtual Safety Car ; le retour au code `"1"` marque sa fin effective |

La colonne `TrackStatus` des tours peut contenir **plusieurs codes concaténés**
si l'état change pendant le tour : un test `.eq("1")` sélectionne seulement
les tours enregistrés entièrement sous le code normal. Ces codes ne sont pas
les valeurs de `fastf1_session_status.Status`, qui contient des mots tels que
`Started`, `Aborted` ou `Finished`.

### Informations qui évitent les mauvaises interprétations

- `DriverNumber` est du texte dans tes tables FastF1 : pour le numéro 1,
  utilise `.eq("1")`. `round_number` et `LapNumber` sont numériques : utilise
  `.eq(1)` ou `.eq(10)` sans guillemets.
- `TyreLife` est l'âge du train de pneus, pas son usure mesurée ni sa durée
  restante. Un train déjà utilisé peut commencer un relais avec un âge non nul.
- `SOFT`, `MEDIUM`, `HARD`, `INTERMEDIATE`, `WET` sont des valeurs de `Compound`.
  Le composé réel associé à Hard/Medium/Soft dépend du GP et de l'année ; il
  n'est pas encore ajouté au catalogue sous forme de référence C1–C6.
- Les abréviations, les équipes et les numéros de cette fiche sont issus des
  résultats locaux 2025. Pour une autre saison ou de nouveaux imports, revérifie
  la table des résultats de la session choisie.

## 1. Démarrer

Dans un terminal ouvert à la racine du projet, avec ton environnement Python activé :

```powershell
kedro jupyter lab
```

Dans la première cellule du notebook :

```ipython
%load_ext kedro.ipython
```

Cela crée notamment la variable `catalog`. C'est elle qui connaît les chemins
des fichiers décrits dans `conf/base/catalog.yml`.

Si l'extension est déjà chargée et que tu veux relire le catalogue :

```ipython
%reload_kedro
```

Un chargement s'écrit en **Python**, avec les guillemets et la parenthèse finale :

```python
laps = catalog.load("fastf1_laps")
laps.head()
```

Les appels `catalog.load(...)` de ce guide lisent les fichiers locaux. Ils ne
téléchargent pas de nouvelles données.

## 2. Comprendre les trois façons de charger FastF1

| Ce que tu veux | Appel à utiliser | Résultat |
| --- | --- | --- |
| Tous les tours déjà préparés de la saison | `catalog.load("fastf1_laps")` | Un DataFrame regroupant les sessions disponibles |
| Les tours d'une seule session | `catalog.load("fastf1_table__round_01__05_race__laps")` | Un DataFrame brut pour cette session |
| La télémétrie d'un seul pilote dans une session | `catalog.load("fastf1_driver__round_01__05_race__car_data__1")` | Un DataFrame brut pour ce pilote |

**L'année est choisie par la configuration Kedro**, pas par le nom de la variable
Python. La valeur par défaut actuelle dans `conf/base/globals.yml` est `2025`.

`fastf1_laps` regroupe aussi les essais, qualifications et sprints disponibles.
Pour avoir uniquement les courses principales, il faut filtrer `session_name`.

Les tables regroupées sont produites par cette commande, à relancer après un
nouvel import :

```powershell
kedro run --pipeline data_preparation
```

Dans ce projet, `kedro run` exécute aussi cette préparation par défaut.
L'import réseau est une commande distincte : `kedro run --pipeline data_ingestion`.

## 3. Savoir quel Grand Prix correspond à `round_01`

`round_01` signifie **première manche de l'année sélectionnée**. Il faut regarder
le calendrier pour connaître son nom. Pour 2025, c'est le GP d'Australie.
`test_01` désigne le premier événement d'essais hivernaux.

```python
schedule = catalog.load("fastf1_schedule")
schedule[["RoundNumber", "EventName", "Country", "EventDate"]]
```

Pour retrouver directement les codes utilisés par le projet :

```python
events = catalog.load("fastf1_events")
events[["event_code", "round_number", "EventName", "Country"]]
```

Un calendrier peut contenir un GP dont les données détaillées ne sont pas encore
installées. La table des sessions ci-dessous sert à vérifier leur présence.

## 4. Choisir la bonne session

Charge la liste des sessions attendues et de leurs fichiers disponibles :

```python
sessions = catalog.load("fastf1_sessions")
sessions[
    ["event_code", "event_name", "session_code", "session_name", "has_laps"]
]
```

Pour afficher seulement les sessions d'Australie qui possèdent un fichier de tours :

```python
sessions.loc[
    sessions["event_code"].eq("round_01") & sessions["has_laps"],
    ["event_name", "session_code", "session_name", "car_data_files", "position_files"],
]
```

Quelques codes présents dans tes données :

| `session_code` | Signification |
| --- | --- |
| `01_practice_1` | Première séance d'essais |
| `02_practice_2` | Deuxième séance d'essais d'un week-end classique |
| `03_practice_3` | Troisième séance d'essais d'un week-end classique |
| `02_sprint_qualifying` | Qualifications du sprint |
| `03_sprint` | Sprint |
| `04_qualifying` | Qualifications du Grand Prix |
| `05_race` | Course principale |

**Recopie le `session_code` de la table, plutôt que de deviner son numéro.**
L'ordre dépend du format du week-end. Les codes sont du texte : il n'existe pas
de session dont le code serait simplement `"0"`.

`has_laps` et `has_results` indiquent la présence d'un fichier. Les colonnes
`car_data_files` et `position_files` comptent les fichiers de pilotes ; elles
ne disent pas si un pilote précis possède son fichier. L'inventaire permet de
le vérifier.

## 5. Savoir à qui correspond le numéro d'une voiture

Dans cet appel :

```python
car_data = catalog.load("fastf1_driver__round_01__05_race__car_data__1")
```

le dernier `1` désigne le **numéro de course du pilote**.
Pour l'Australie 2025, c'est **Max Verstappen, Red Bull Racing**.

Le nom complet se décompose ainsi :

```text
fastf1_driver__round_01__05_race__car_data__1
               événement  session   table  numéro du pilote
```

Pour obtenir la correspondance exacte dans la session choisie :

```python
pilotes = catalog.load("fastf1_table__round_01__05_race__results")
pilotes[["DriverNumber", "Abbreviation", "FullName", "TeamName"]]
```

Pour afficher les pilotes Red Bull de cette session :

```python
pilotes_red_bull = pilotes.loc[
    pilotes["TeamName"].eq("Red Bull Racing"),
    ["DriverNumber", "Abbreviation", "FullName", "TeamName"],
]
pilotes_red_bull
```

**Vérifie les résultats de chaque session : les pilotes et leurs équipes peuvent
changer au cours d'une saison.** `Red Bull Racing` et `Racing Bulls` sont deux
équipes distinctes dans les données.

### Choisir par nom abrégé au lieu de connaître le numéro

```python
event_code = "round_01"
session_code = "05_race"
abbreviation = "VER"

pilotes = catalog.load(f"fastf1_table__{event_code}__{session_code}__results")
selection = pilotes.loc[pilotes["Abbreviation"].eq(abbreviation)]

if selection.empty:
    raise ValueError(f"Pilote {abbreviation} absent de cette session")

pilote = selection.iloc[0]
numero = str(pilote["DriverNumber"])

car_data = catalog.load(
    f"fastf1_driver__{event_code}__{session_code}__car_data__{numero}"
)
position = catalog.load(
    f"fastf1_driver__{event_code}__{session_code}__position__{numero}"
)

print(pilote["FullName"], "—", pilote["TeamName"])
print("Télémétrie :", car_data.shape)
```

Les accolades des modèles du catalogue sont remplacées par les valeurs de tes
variables grâce au `f` placé devant la chaîne de caractères.

## 6. Toutes les tables préparées : appel et contenu

Ces tables regroupent les fichiers locaux de l'année sélectionnée.
Elles se trouvent dans `data/03_primary/fastf1/<année>/`.

| Nom dans le catalogue | Contenu principal | Ce que représente une ligne |
| --- | --- | --- |
| `fastf1_events` | Nom du GP, pays, dates, format et programme des sessions | Un événement |
| `fastf1_laps` | Pilote, tour, chrono, secteurs, pneus, position, indicateurs de validité | Un tour d'un pilote |
| `fastf1_results` | Pilote, équipe, classement, grille, Q1/Q2/Q3, points, statut | Le résultat d'un pilote dans une session |
| `fastf1_weather` | Températures, pluie, humidité, vent, pression atmosphérique | Un relevé météo |
| `fastf1_stints` | Pilote, gomme, premier/dernier tour, nombre de tours, âge des pneus | Un relais |
| `fastf1_pit_events` | Colonnes des tours, filtrées sur une entrée ou sortie des stands | Un tour concerné par un passage aux stands |
| `fastf1_track_status` | `Time`, `Status`, `Message` | Un état de piste horodaté |
| `fastf1_session_status` | `Time`, `Status` | Un état de session horodaté |
| `fastf1_race_control` | Heure, catégorie, message, drapeau, pilote, tour et secteur concernés | Un message de direction de course |
| `fastf1_circuit_corners` | `X`, `Y`, `Number`, `Letter`, `Angle`, `Distance` | Un repère de virage dans une session |
| `fastf1_circuit_marshal_lights` | Coordonnées et repères des feux des commissaires | Un repère dans une session |
| `fastf1_circuit_marshal_sectors` | Coordonnées et repères des secteurs des commissaires | Un repère dans une session |
| `fastf1_circuit_rotation` | `rotation` | La rotation du tracé pour une session |

Voici chaque appel, utilisable individuellement :

```python
events = catalog.load("fastf1_events")
laps = catalog.load("fastf1_laps")
results = catalog.load("fastf1_results")
weather = catalog.load("fastf1_weather")
stints = catalog.load("fastf1_stints")
pit_events = catalog.load("fastf1_pit_events")
track_status = catalog.load("fastf1_track_status")
session_status = catalog.load("fastf1_session_status")
race_control = catalog.load("fastf1_race_control")
circuit_corners = catalog.load("fastf1_circuit_corners")
circuit_marshal_lights = catalog.load("fastf1_circuit_marshal_lights")
circuit_marshal_sectors = catalog.load("fastf1_circuit_marshal_sectors")
circuit_rotation = catalog.load("fastf1_circuit_rotation")
```

Les cinq colonnes ajoutées par la préparation identifient l'origine de chaque ligne :

| Colonne | Exemple | Signification |
| --- | --- | --- |
| `year` | `2025` | Saison |
| `event_code` | `round_01` | Dossier de l'événement |
| `round_number` | `1` | Manche ; `0` pour les essais hivernaux |
| `session_code` | `05_race` | Dossier de la session |
| `session_name` | `race` | Nom simplifié de la session |

Dans `fastf1_events`, les champs de contexte de session sont vides puisque la
ligne décrit l'événement entier. Les informations de programme se trouvent dans
`Session1`, `Session1Date`, etc. Les repères d'un même circuit peuvent se répéter
entre les sessions.

### Filtrer les tables préparées

```python
# Toutes les courses principales disponibles.
courses = laps.loc[laps["session_name"].eq("race")]

# La course principale de l'Australie.
australie = courses.loc[courses["event_code"].eq("round_01")]

# Red Bull sur cette course.
red_bull = australie.loc[australie["Team"].eq("Red Bull Racing")]

# Verstappen uniquement.
verstappen = australie.loc[australie["Driver"].eq("VER")].copy()
verstappen[["Driver", "LapNumber", "Compound", "TyreLife", "LapTime"]].head()
```

Les colonnes varient selon la table : dans `laps`, l'équipe est `Team` et le
pilote abrégé est `Driver`. Dans `results`, ce sont `TeamName` et `Abbreviation`.
La météo n'a pas de pilote : elle décrit une session.

## 7. Charger une seule session, sans charger toute la saison

Le modèle général est :

```text
fastf1_table__{event}__{session}__{table}
```

Exemples pour la course d'Australie :

```python
laps_session = catalog.load("fastf1_table__round_01__05_race__laps")
results_session = catalog.load("fastf1_table__round_01__05_race__results")
weather_session = catalog.load("fastf1_table__round_01__05_race__weather")
stints_session = catalog.load("fastf1_table__round_01__05_race__stints")
pit_events_session = catalog.load("fastf1_table__round_01__05_race__pit_events")
track_status_session = catalog.load("fastf1_table__round_01__05_race__track_status")
session_status_session = catalog.load("fastf1_table__round_01__05_race__session_status")
race_control_session = catalog.load("fastf1_table__round_01__05_race__race_control")
corners_session = catalog.load("fastf1_table__round_01__05_race__circuit_corners")
lights_session = catalog.load("fastf1_table__round_01__05_race__circuit_marshal_lights")
sectors_session = catalog.load("fastf1_table__round_01__05_race__circuit_marshal_sectors")
rotation_session = catalog.load("fastf1_table__round_01__05_race__circuit_rotation")
```

**Ce sont des fichiers bruts** : ils n'ont pas les cinq colonnes de contexte
ajoutées par la préparation et conservent les types de l'export d'origine.
Leur événement et leur session sont ceux indiqués dans le nom chargé.

Ces accès fonctionnent avant la préparation, si le fichier demandé existe.
Un fichier absent produit une erreur ; il n'est pas téléchargé automatiquement.

## 8. Charger la télémétrie et les coordonnées d'une voiture

Le modèle général est :

```text
fastf1_driver__{event}__{session}__{table}__{driver}
```

Deux valeurs de `table` sont présentes dans tes exports :

| Table | Données |
| --- | --- |
| `car_data` | `Date`, `Time`, `SessionTime`, `Speed`, `RPM`, `nGear`, `Throttle`, `Brake`, `DRS`, `Source` |
| `position` | `Date`, `Time`, `SessionTime`, `X`, `Y`, `Z`, `Status`, `Source` |

```python
car_data = catalog.load("fastf1_driver__round_01__05_race__car_data__1")
position = catalog.load("fastf1_driver__round_01__05_race__position__1")

car_data[["SessionTime", "Speed", "RPM", "nGear", "Throttle", "Brake"]].head()
```

`position` contient les **coordonnées spatiales** de la voiture. Le classement
à la fin de chaque tour se trouve dans la colonne `Position` de `laps`.

Le numéro, le nom et l'équipe ne sont pas répétés dans les colonnes brutes de
ces fichiers : retrouve-les dans les résultats de la session, comme en section 5.
Les fichiers sont séparés par pilote pour éviter de charger toute la télémétrie
de l'année en mémoire. Il n'existe actuellement pas d'entrée globale
`fastf1_car_data` dans le catalogue.

### Pourquoi les premières lignes peuvent être à zéro

Les fichiers peuvent contenir des mesures avant le début de la course, lorsque
la voiture est immobile. Pour voir quelques mesures en mouvement :

```python
print(car_data.shape)
print("Table vide :", car_data.empty)

car_data.loc[
    car_data["Speed"].gt(0),
    ["SessionTime", "Speed", "RPM", "nGear", "Throttle", "Brake"],
].head(10)
```

Ce filtre sert à explorer les données. Une vitesse positive ne suffit pas à
identifier un tour de course : la voiture peut aussi rouler avant le départ.

### Récupérer la télémétrie d'un tour précis

Utilise les limites du tour et l'horloge de session `SessionTime` :

```python
laps_session = catalog.load("fastf1_table__round_01__05_race__laps")
tour = laps_session.loc[
    laps_session["Driver"].eq("VER") & laps_session["LapNumber"].eq(10)
].iloc[0]

telemetrie_tour_10 = car_data.loc[
    car_data["SessionTime"].ge(tour["LapStartTime"])
    & car_data["SessionTime"].lt(tour["Time"])
].copy()

telemetrie_tour_10[["SessionTime", "Speed", "RPM", "Throttle", "Brake"]].head()
```

Le fichier `car_data` et la ligne de tour doivent correspondre **au même pilote,
au même événement et à la même session**. Vérifie l'existence du tour et de ses
horodatages avant d'adapter cet exemple à une autre session.

## 9. Calendrier, inventaire et rapports

```python
schedule = catalog.load("fastf1_schedule")
sessions = catalog.load("fastf1_sessions")
inventory = catalog.load("fastf1_inventory")
ingestion_report = catalog.load("fastf1_ingestion_report")
```

| Table | À quoi elle sert | Colonnes utiles |
| --- | --- | --- |
| `fastf1_schedule` | Lire le programme de la saison | `RoundNumber`, `EventName`, `Session1` à `Session5`, dates |
| `fastf1_sessions` | Choisir une session et vérifier la présence de fichiers | `event_code`, `event_name`, `session_code`, `has_laps`, `has_results`, `car_data_files`, `position_files`, `file_count` |
| `fastf1_inventory` | Retrouver chaque fichier d'événement/session reconnu | `year`, `event_code`, `round_number`, `session_code`, `session_name`, `table`, `driver_number`, `partition` |
| `fastf1_ingestion_report` | Consulter le compte rendu du dernier import terminé | `year`, `event`, `round`, `session`, `dataset`, `driver`, `status`, `rows`, `path`, `message`, `utc` |

Voir les pilotes pour lesquels un fichier de télémétrie existe en Australie :

```python
inventory.loc[
    inventory["event_code"].eq("round_01")
    & inventory["session_code"].eq("05_race")
    & inventory["table"].eq("car_data"),
    ["driver_number", "partition"],
]
```

Voir les sessions sans fichier de tours :

```python
sessions.loc[~sessions["has_laps"], ["event_name", "session_name"]]
```

Le rapport d'import peut être plus ancien que certains fichiers bruts.
L'inventaire et les indicateurs de présence sont actualisés par la préparation.
Ils ne garantissent pas que les données d'un fichier sont complètes.

## 10. Explorer les fichiers bruts avec les partitions

```python
partitions = catalog.load("fastf1_raw")
list(partitions)[:10]
```

**Ici, `partitions` est un dictionnaire, pas un DataFrame.** Ses valeurs sont
des fonctions de lecture. Les parenthèses à la fin lisent le fichier choisi :

```python
raw_laps = partitions["round_01/05_race/laps"]()
raw_car_data = partitions["round_01/05_race/car_data/1"]()
```

Les clés sont relatives au dossier de l'année et ne contiennent pas `.parquet`.
Ce dictionnaire inclut aussi le calendrier (`schedule`) et les fiches
d'événement (par exemple `round_01/event`).

Pour voir seulement les clés de télémétrie du GP d'Australie :

```python
car_keys = sorted(
    key for key in partitions
    if key.startswith("round_01/05_race/car_data/")
)
car_keys
```

## 11. Charger OpenF1

OpenF1 est une autre source. Ses noms de colonnes et identifiants diffèrent de
FastF1. Ne mélange pas directement leurs tables.

Les deux calendriers :

```python
openf1_meetings = catalog.load("openf1_meetings")
openf1_sessions = catalog.load("openf1_sessions")

openf1_sessions[
    ["session_key", "session_name", "session_type", "location", "date_start"]
].head()
```

| Entrée | Contenu |
| --- | --- |
| `openf1_meetings` | Événements : `meeting_key`, noms, pays, circuit, dates, année |
| `openf1_sessions` | Sessions : `session_key`, type, nom, dates, événement et circuit |

Le modèle d'accès détaillé est :

```text
openf1_table__{session_key}__{table}
```

`session_key` est l'identifiant OpenF1. **Ce n'est pas le numéro de manche.**
Dans les fichiers vérifiés le 24 octobre 2026, les tables détaillées suivantes
sont présentes pour la clé `9683` :

```python
openf1_drivers = catalog.load("openf1_table__9683__drivers")
openf1_laps = catalog.load("openf1_table__9683__laps")
openf1_pit = catalog.load("openf1_table__9683__pit")
openf1_position = catalog.load("openf1_table__9683__position")
openf1_race_control = catalog.load("openf1_table__9683__race_control")
openf1_results = catalog.load("openf1_table__9683__session_result")
openf1_stints = catalog.load("openf1_table__9683__stints")
openf1_weather = catalog.load("openf1_table__9683__weather")
```

| Table détaillée | Informations principales |
| --- | --- |
| `drivers` | Numéro, nom, abréviation, équipe : `driver_number`, `full_name`, `name_acronym`, `team_name` |
| `laps` | Numéro de tour, durée, secteurs et vitesses : `lap_number`, `lap_duration`, `duration_sector_1`... |
| `pit` | Événements des stands et champs de durée : `pit_duration`, `lane_duration`, `stop_duration` |
| `position` | Classement au fil du temps : `date`, `position`, `driver_number` |
| `race_control` | Messages, drapeaux, tours et secteurs concernés |
| `session_result` | Classement final, nombre de tours, durée, écart, DNF/DNS/DSQ |
| `stints` | Gomme, limites du relais et âge initial des pneus |
| `weather` | Températures, pluie, humidité, pression et vent |

Contrairement au fichier FastF1 `position`, **OpenF1 `position` contient le
classement, pas les coordonnées X/Y/Z**. Un calendrier OpenF1 complet ne signifie
pas que les détails de toutes ses sessions sont installés.

## 12. Inspecter une table et éviter les confusions

Ces commandes fonctionnent pour les DataFrames, pas pour le dictionnaire de partitions :

```python
df = catalog.load("fastf1_laps")

print("Lignes, colonnes :", df.shape)
print("Vide :", df.empty)
print("Colonnes :", df.columns.tolist())
df.head()
```

Pour les chronos FastF1, conserve la durée d'origine et crée une colonne en secondes :

```python
verstappen["lap_time_seconds"] = verstappen["LapTime"].dt.total_seconds()
verstappen[["LapNumber", "LapTime", "lap_time_seconds"]].head()
```

| Si tu observes ceci | Explication ou vérification |
| --- | --- |
| `NameError: catalog` | Charger l'extension Kedro dans le notebook |
| `NameError: laps` | Exécuter d'abord la cellule qui crée `laps` |
| Une table vide après un filtre | Vérifier les valeurs et les types avec `.unique()` ; `session_code` ne vaut pas `"0"` |
| Des zéros au début de `car_data` | Vérifier `.shape` et les mesures suivantes ; la voiture peut être immobile |
| Un fichier introuvable | Vérifier année, événement, session, pilote et présence dans l'inventaire |
| Une entrée `fastf1_car_data` introuvable | Utiliser le modèle par pilote ou `fastf1_raw` ; cette entrée globale n'est pas définie |
| `Pressure` dans `weather` | Pression atmosphérique ; aucune pression de pneu dans cette table |
| `TrackTemp` | Température de piste ; aucune température interne des pneus dans cette colonne |
| `TyreLife` | Âge du train de pneus en tours ; ce n'est pas le nombre de tours qu'il reste à faire |
| Plusieurs lignes dans `pit_events` pour un passage | Les tours d'entrée et de sortie peuvent être distincts ; une ligne n'est pas un arrêt unique |

Pour vérifier les valeurs possibles avant un filtre :

```python
laps["session_code"].unique()
laps["Driver"].unique()
laps["Team"].unique()
```

## 13. Changer l'année

Dans un notebook :

```ipython
%reload_kedro --params year=2024
```

Dans le terminal, pour préparer cette année :

```powershell
kedro run --pipeline data_preparation --params year=2024
```

Ces commandes ne créent pas les données brutes manquantes. Il faut que le
calendrier et les fichiers de 2024 soient déjà installés pour les charger.
Leurs chemins et les paramètres utilisent la même année.

Après un changement d'année, **recharge tes variables avec `catalog.load(...)`** :
un ancien DataFrame déjà chargé reste celui de l'année précédente.

Pour revenir aux données utilisées dans les exemples de ce guide :

```ipython
%reload_kedro --params year=2025
```

## 14. Exemple complet à copier : choisir Verstappen et lire ses données

Exécute d'abord `%load_ext kedro.ipython` ou `%reload_kedro`, puis cette cellule :

```python
event_code = "round_01"       # Australie pour l'année 2025
session_code = "05_race"     # Course principale
abbreviation = "VER"        # Pilote voulu

# 1. Identifier le pilote dans cette session.
pilotes = catalog.load(f"fastf1_table__{event_code}__{session_code}__results")
selection = pilotes.loc[pilotes["Abbreviation"].eq(abbreviation)]
if selection.empty:
    raise ValueError(f"Pilote {abbreviation} absent de cette session")
pilote = selection.iloc[0]
numero = str(pilote["DriverNumber"])

# 2. Charger les tours de la session et sélectionner ce pilote.
laps_session = catalog.load(f"fastf1_table__{event_code}__{session_code}__laps")
laps_pilote = laps_session.loc[laps_session["DriverNumber"].eq(numero)].copy()
laps_pilote["lap_time_seconds"] = laps_pilote["LapTime"].dt.total_seconds()

# 3. Charger la télémétrie et les coordonnées de sa voiture.
car_data = catalog.load(
    f"fastf1_driver__{event_code}__{session_code}__car_data__{numero}"
)
position = catalog.load(
    f"fastf1_driver__{event_code}__{session_code}__position__{numero}"
)

# 4. Charger les conditions de cette session.
weather = catalog.load(f"fastf1_table__{event_code}__{session_code}__weather")

print(pilote["FullName"], "—", pilote["TeamName"], "— numéro", numero)
print("Événement :", event_code, "| Session :", session_code)
print("Tours :", len(laps_pilote), "| Mesures voiture :", len(car_data))
laps_pilote[["Driver", "LapNumber", "Compound", "TyreLife", "lap_time_seconds"]].head()
```

Adapte les trois variables du début en vérifiant d'abord les tables `events`,
`sessions` et `pilotes`. Garde toutes les équipes dans les données sources si tu
veux ensuite étudier les adversaires de Red Bull.
