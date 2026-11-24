# Lectures pour le projet de stratégie Red Bull

Sélection vérifiée le 24 octobre 2026. Six PDF originaux téléchargés depuis les sites des éditeurs, arXiv, le site du workshop ou un dépôt scientifique. Les noms locaux sont descriptifs ; le contenu des PDF est inchangé. Les documents sont en anglais.

L'objectif est d'estimer les conséquences de plusieurs décisions de pit stop, puis de choisir une stratégie selon un objectif explicite. Le fait de prédire un arrêt historiquement observé ne suffit pas à établir son optimalité.

## Ordre de lecture conseillé

1. **Heilmeier et al. (2020), Virtual Strategy Engineer: Using Artificial Neural Networks for Making Race Strategy Decisions in Circuit Motorsport.**
   Fichier : `01_Heilmeier_2020_Virtual_Strategy_Engineer.pdf` (33 pages, couverture incluse).
   Priorité : première lecture. Lire notamment la section 4.1 sur l'optimisation de base puis la section 4.4 sur l'intégration au simulateur. Utile pour comprendre les longueurs de relais, la dégradation et la séparation entre choix du tour et choix de la gomme. Le VSE supervisé apprend aussi des décisions historiques ; il faut distinguer cette partie du modèle d'optimisation simplifié et des évaluations par simulation.
   Code et données cités par les auteurs : https://github.com/TUMFTM/race-simulation et https://github.com/TUMFTM/f1-timing-database.

2. **Heilmeier et al. (2020), Application of Monte Carlo Methods to Consider Probabilistic Effects in a Race Simulation for Circuit Motorsport.**
   Fichier : `02_Heilmeier_2020_Simulation_Monte_Carlo.pdf` (21 pages).
   Priorité : construire un simulateur et mesurer l'incertitude. Le modèle de temps au tour combine plusieurs contributions ; les scénarios probabilistes traitent les variations de performance, les arrêts, les incidents et les périodes de Safety Car. Utile pour comparer le temps moyen et le risque des stratégies. Les paramètres doivent être recalibrés sur la saison et les circuits étudiés.

3. **Piccinotti et al. (2021), Online Planning for F1 Race Strategy Identification.**
   Fichier : `03_Piccinotti_2021_Planification_Strategie_F1.pdf` (11 pages).
   Statut : article du workshop PRL à ICAPS 2021, et non article principal des actes AAAI.
   Priorité : passer à la décision tour par tour. Modélisation par processus de décision markovien, recherche arborescente Monte Carlo et mises à jour de type Q-learning. Les actions sont continuer ou s'arrêter pour une gomme disponible. Les sections 4 et 5 donnent le cadre et l'algorithme. Les adversaires ne sont pas tous des agents optimisés simultanément. Le choix d'une récompense fondée sur le temps peut produire un classement moins bon ; cette limite est discutée dans l'article.

4. **Thomas et al. (2026), Race Strategy Reinforcement Learning: Optimising Pitstop Strategy with Emergent Tactics in Formula One.**
   Fichier : `04_Thomas_2026_RSRL_Strategie_Explicable.pdf` (31 pages).
   Publication : Machine Learning, 9 juin 2026.
   Priorité : prolongement avancé. Apprentissage par renforcement, explication des décisions, généralisation à d'autres circuits et étude tactique. Les auteurs incluent Imperial College London et Mercedes-AMG PETRONAS. La validation utilise un simulateur et des données Mercedes propriétaires, donc sa reproduction complète n'est pas possible avec FastF1 seul.
   Code cité : https://github.com/DevinThomas185/F1-RSRL/.

5. **Avella et al. (2026), A simulation framework for Formula 1 race strategy based on pit-stop optimization.**
   Fichier : `05_Avella_2026_Optimisation_Simulation.pdf` (36 pages).
   Version téléchargée : manuscrit déposé sur Optimization Online dans le répertoire de février 2026.
   Priorité : approfondissement en optimisation mathématique. Le modèle combine longueurs de relais, gommes, carburant et gestion ERS pour minimiser le temps de course. La section 4 décrit le modèle et les contraintes ; la section 5 décrit une validation comprenant des simulateurs de conduite. Pour le prototype, isoler d'abord pneus et pit stops : plusieurs paramètres du modèle complet ne sont pas directement observables dans les tables FastF1 disponibles.

6. **Thomas et al. (2025), Explainable Reinforcement Learning for Formula One Race Strategy.**
   Fichier : `06_Thomas_2025_RL_Explicable_Version_Courte.pdf` (9 pages).
   Priorité : introduction courte au numéro 4. Il s'agit du travail antérieur, ensuite étendu en 2026, et non d'une méthode indépendante supplémentaire. Lire cette version d'abord si le document de 31 pages est trop dense.

## Application à ce projet

- Commencer par les courses principales et un périmètre défini, par exemple une voiture Red Bull sur piste sèche.
- Estimer la performance des gommes et la perte totale d'un passage aux stands à partir des données disponibles ; contrôler l'effet du trafic et de l'évolution du rythme.
- Comparer un ensemble de stratégies simples, puis les tester sur des courses distinctes de celles utilisées pour ajuster les paramètres.
- Ajouter ensuite des scénarios probabilistes et une décision réévaluée à chaque tour.
- Conserver les données des autres pilotes pour représenter le trafic et la concurrence, même si les recommandations visent Red Bull.
- Une stratégie est optimale relativement au modèle, aux informations disponibles et à l'objectif choisi. Les résultats en simulation doivent être présentés avec leurs hypothèses.

Les URL originales, les tailles et les empreintes des fichiers se trouvent dans `sources.json`.
