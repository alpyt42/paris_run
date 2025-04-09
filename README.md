# Paris Run - Visualisation des Tracés GPX

Ce projet permet de visualiser et d'explorer les tracés GPX de courses à pied à Paris. L'application web utilise Streamlit pour créer une interface interactive pour visualiser les tracés sur une carte, animer le passage de relais entre segments et explorer les détails de chaque segment.

## Fonctionnalités

- 📊 **Vue d'ensemble des tracés** : visualisation simultanée de tous les segments sur une carte interactive.
- 🎬 **Animation des relais** : animation montrant l'enchaînement des segments dans le temps.
- 🔍 **Détails des tracés** : exploration des caractéristiques de chaque segment.
- 🗺️ **Export vers Google Maps** : possibilité d'exporter un segment vers Google Maps.
- 📥 **Téléchargement GPX** : téléchargement des segments au format GPX.

## Installation

### Prérequis

- [Anaconda](https://www.anaconda.com/products/individual) ou [Miniconda](https://docs.conda.io/en/latest/miniconda.html)
- Git (pour cloner ce dépôt)

### Étapes d'installation

1. **Cloner le dépôt** (si ce n'est pas déjà fait) :
   ```bash
   git clone <URL-du-dépôt>
   cd paris_run
   ```

2. **Créer l'environnement Conda** à partir du fichier `environment.yml` :
   ```bash
   conda env create -f environment.yml
   ```
   Cette commande va créer un environnement nommé `env_code_test` avec toutes les dépendances nécessaires.

3. **Activer l'environnement** :
   ```bash
   conda activate env_code_test
   ```

## Utilisation de l'application

### Lancer l'application Streamlit

1. Assurez-vous que l'environnement conda est activé :
   ```bash
   conda activate env_code_test
   ```

2. Lancez l'application Streamlit :
   ```bash
   streamlit run display_all_traces.py
   ```
   
3. Votre navigateur web par défaut devrait s'ouvrir automatiquement avec l'application. Si ce n'est pas le cas, ouvrez votre navigateur et accédez à l'URL indiquée dans le terminal (généralement `http://localhost:8501`).

### Navigation dans l'application

L'application est divisée en trois onglets :

1. **📊 Carte des tracés** : 
   - Visualisez tous les segments sur une carte interactive
   - Utilisez les filtres dans la barre latérale pour sélectionner les segments à afficher
   - Affichez les statistiques détaillées des segments sélectionnés

2. **🎬 Animation des relais** :
   - Regardez l'animation des segments s'enchaînant l'un après l'autre
   - Utilisez les boutons Play/Pause/Reset pour contrôler l'animation
   - Ajustez le nombre de segments à animer pour optimiser les performances

3. **🔍 Détail d'un tracé** :
   - Sélectionnez un segment spécifique pour l'examiner en détail
   - Consultez les statistiques précises (distance, nombre de points)
   - Exportez le tracé vers Google Maps ou téléchargez-le au format GPX

## Optimisation des performances

Si vous rencontrez des problèmes de performance (lenteur lors du zoom/dézoom) :

1. Réduisez le nombre de segments affichés avec le filtre "Limiter le nombre de segments"
2. Désactivez l'affichage des marqueurs de début/fin de segments
3. Utilisez le bouton "Vider le cache" dans la barre latérale si l'application devient lente
4. Utilisez le bouton "Rafraîchir la carte" pour recharger l'affichage

## Structure des données

L'application utilise les fichiers GPX stockés dans différents dossiers :
- `Relais_gpx_dp` : Tracés par défaut
- `Relais_gpx_greedy` : Tracés avec algorithme glouton
- `Relais_gpx_optimized` : Tracés optimisés
- `Relais_gpx` : Tracés originaux

Chaque fichier GPX représente un segment de course distinct.

## Dépannage

- **Problème** : La carte ne s'affiche pas correctement
  **Solution** : Cliquez sur "Rafraîchir la carte" ou videz le cache

- **Problème** : Les animations sont lentes
  **Solution** : Réduisez le nombre de segments à animer

- **Problème** : L'application crash avec une erreur de mémoire
  **Solution** : Redémarrez l'application et limitez le nombre de segments affichés

## Désinstallation de l'environnement

Si vous souhaitez supprimer l'environnement conda :
```bash
conda deactivate
conda env remove -n env_code_test
