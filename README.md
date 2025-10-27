# Optimiseur de Tournées de Ramassage - Boîtes à Habits

## Description

Cette application aide les chauffeurs de camion à optimiser leurs tournées de ramassage des boîtes à habits dans le canton de Genève. Elle recommande les boîtes les plus susceptibles d'être pleines en se basant sur l'historique de remplissage et le temps écoulé depuis la dernière visite.

## Fonctionnalités

- **Analyse prédictive** : Calcule la probabilité de remplissage de chaque boîte
- **Optimisation des tournées** : Recommande les boîtes les plus rentables à visiter
- **Apprentissage continu** : Le système s'améliore avec chaque visite enregistrée
- **Interface web** : Interface utilisateur intuitive pour les chauffeurs
- **Interface en ligne de commande** : Pour les tests et l'utilisation avancée

## Installation

1. **Prérequis** :
   - Python 3.7 ou plus récent
   - Fichier de données `ml_boxes_ready.csv`

2. **Installation des dépendances** :
   ```bash
   pip install -r requirements.txt
   ```

## Utilisation

### Interface Web (Recommandée)

1. **Lancement** :
   ```bash
   python app.py
   ```
   ou utilisez les scripts de lancement :
   - Windows : `start.bat`
   - Linux/Mac : `./start.sh`

2. **Accès** : Ouvrez votre navigateur sur `http://localhost:5000`

3. **Fonctionnalités** :
   - Consultez les recommandations de boîtes
   - Marquez vos visites avec le niveau de remplissage observé
   - Le système met à jour automatiquement les recommandations

### Interface en Ligne de Commande

1. **Lancement** :
   ```bash
   python box_collection_optimizer.py
   ```

2. **Démonstration** :
   ```bash
   python demo.py
   ```

3. **Tests** :
   ```bash
   python test_app.py
   ```

## Algorithme de Scoring

Le score de rentabilité est calculé en combinant :

1. **Remplissage historique** (40%) : Moyenne des 52 semaines de 2024
2. **Tendance récente** (30%) : Évolution des 4 dernières semaines
3. **Urgence temporelle** (30%) : Temps écoulé depuis la dernière visite

### Formule
```
Score = (Remplissage_historique × 0.4) + (Tendance_récente × 0.3) + (Urgence_temporelle × 0.3)
```

## Structure des Données

Le fichier `ml_boxes_ready.csv` doit contenir :
- `n_boite` : Numéro de la boîte
- `adresse` : Adresse complète
- `commune` : Commune
- `cp` : Code postal
- `conteneur` : Type de conteneur
- `semaine_1` à `semaine_52` : Niveaux de remplissage hebdomadaires (0-10)
- `volume_moyen` : Moyenne du remplissage

## Fichiers de l'Application

- `box_collection_optimizer.py` : Logique principale de l'optimiseur
- `app.py` : Application Flask (interface web)
- `templates/index.html` : Interface utilisateur web
- `static/css/style.css` : Styles CSS
- `static/js/app.js` : JavaScript côté client
- `config.py` : Configuration de l'application
- `demo.py` : Script de démonstration
- `test_app.py` : Tests de l'application
- `requirements.txt` : Dépendances Python
- `start.bat` / `start.sh` : Scripts de lancement

## État de l'Application

L'application sauvegarde automatiquement l'état dans `optimizer_state.json` :
- Historique des visites
- Dates de dernière visite pour chaque boîte
- Données d'apprentissage

## Conseils d'Utilisation

1. **Priorité** : Visitez d'abord les boîtes avec le score le plus élevé
2. **Enregistrement** : Marquez toujours vos visites avec le niveau de remplissage observé
3. **Apprentissage** : Le système s'améliore avec chaque visite enregistrée
4. **Optimisation** : Les boîtes non visitées depuis longtemps ont une priorité élevée

## Support

Pour toute question ou problème :
1. Vérifiez que le fichier `ml_boxes_ready.csv` est présent
2. Exécutez `python test_app.py` pour diagnostiquer les problèmes
3. Consultez les logs d'erreur dans la console

## Licence

Application développée pour l'optimisation des tournées de ramassage des boîtes à habits dans le canton de Genève.