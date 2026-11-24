# Audit initial — 2 novembre 2026

Diagnostic effectué avant modification des modules et des données sportives.
Environnement : Conda `verstappen`, Python 3.14.9, FastF1 3.9.0, Pandas 2.3.3.

| Saison | Parquet bruts | Taille (octets) | Sessions avec tours | Courses avec tours |
| --- | ---: | ---: | ---: | --- |
| 2024 | 0 | 0 | 0 | aucune |
| 2025 | 5682 | 2956068780 | 109 / 123 au calendrier local | manches 1 à 21 |

Les 5682 en-têtes sont lisibles et annoncent au moins une ligne. Ce contrôle ne
prouve ni la lecture de toutes les pages ni l'exhaustivité des observations.
Cache : 1117 fichiers, 8310092701 octets. Environ 79 Go libres avant travaux.
Mesures conservées dans `data/08_reporting/mission_2024_2025/initial_inventory.json`.

## Inspection

Inventaire de l'arborescence complète ; lecture des modules source, pipelines,
registre Kedro, configurations, dépendances, tests, README, guide, documentation
de configuration et journaux. Les notebooks et bibliographies sont conservés.
Aucun AGENTS.md trouvé dans le projet ou ses parents inspectés. Pas de dossier
`.git` dans ce checkout. Les exports OpenF1 restent séparés et ne sont pas utilisés.

## Défauts confirmés

- `valid_parquet` ne lit que les métadonnées ; `save_table` saute tout fichier
  lisible sans comparer les lignes, pilotes, bornes temporelles ni schémas.
- Une session est rechargée même quand ses fichiers sont déjà présents ; aucune
  preuve persistante de comparaison source ne permet de la sauter sûrement.
- Pas de sauvegarde de l'original lors du remplacement d'un fichier défectueux.
- Pas de reprise contrôlée des exceptions réseau ; les derniers logs contiennent
  `RateLimitExceededError: any API: 500 calls/h`.
- Inventaire et `has_laps` ne mesurent que la présence. Les rapports préparés
  peuvent être plus anciens que les bruts.
- `pit_events` conserve des tours d'entrée/sortie, pas des arrêts appariés.
- Les propriétés publiques `session_info`, `t0_date`, `session_start_time`,
  `total_laps` et la liste des pilotes ne sont pas exportées explicitement.
- Les booléens objets deviennent des chaînes dans le brut. Seul IsPersonalBest
  est normalisé dans la préparation.
- Pas de couche de contrôles scientifiques ni de comparaison inter-schémas.

## Principes de correction

Conserver les partitions année/événement/session/pilote, les interfaces FastF1
publiques, le cache, les colonnes originales et les accès Kedro existants.
Une donnée exportée intégralement depuis FastF1 peut malgré tout être incomplète
à la source : distinguer fidélité de l'export et anomalies scientifiques.
Ne pas imposer 20 pilotes, un nombre universel de tours ou cinq sessions aux essais.
Conserver les anomalies et les observations `FastF1Generated` sans les présenter
comme des mesures directes. Le texte de mission reçu s'arrête à la section 5.
