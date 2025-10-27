# Configuration pour l'optimiseur de tournées de boîtes à habits

# Paramètres de scoring
SCORING_CONFIG = {
    # Poids des différents facteurs dans le score de rentabilité
    'FILL_WEIGHT': 6,      # Poids du remplissage attendu (sur 10)
    'URGENCY_WEIGHT': 4,   # Poids de l'urgence (sur 10)
    
    # Seuils d'urgence (en jours)
    'URGENCY_THRESHOLDS': {
        'HIGH': 14,        # Plus de 14 jours = urgence maximale
        'MEDIUM': 7,       # 7-14 jours = urgence élevée
        'LOW': 3           # 3-7 jours = urgence moyenne
    },
    
    # Nombre de semaines d'historique à considérer
    'HISTORY_WEEKS': 4,
    
    # Bonus maximum pour la tendance croissante
    'MAX_TREND_BONUS': 2.0,
    
    # Facteur de temps maximum
    'MAX_TIME_FACTOR': 2.0
}

# Paramètres de l'interface web
WEB_CONFIG = {
    'HOST': '0.0.0.0',
    'PORT': 5000,
    'DEBUG': True,
    'SECRET_KEY': 'your-secret-key-here'
}

# Paramètres par défaut pour les recommandations
DEFAULT_RECOMMENDATIONS = {
    'MAX_BOXES': 20,
    'MIN_SCORE': 30.0,
    'DEFAULT_COMMUNE_FILTER': ''
}

# Paramètres de sauvegarde
SAVE_CONFIG = {
    'STATE_FILE': 'optimizer_state.json',
    'AUTO_SAVE': True,
    'BACKUP_COUNT': 5
}

# Messages d'interface
MESSAGES = {
    'WELCOME': 'Bienvenue dans l\'optimiseur de tournées de boîtes à habits',
    'NO_RECOMMENDATIONS': 'Aucune boîte ne correspond aux critères sélectionnés',
    'VISIT_RECORDED': 'Visite enregistrée avec succès',
    'ERROR_LOADING': 'Erreur lors du chargement des données',
    'ERROR_SAVING': 'Erreur lors de la sauvegarde'
}

# Couleurs pour l'interface
COLORS = {
    'EXCELLENT_SCORE': '#28a745',    # Vert
    'GOOD_SCORE': '#17a2b8',         # Bleu
    'AVERAGE_SCORE': '#ffc107',      # Jaune
    'POOR_SCORE': '#dc3545',         # Rouge
    'HIGH_URGENCY': '#dc3545',       # Rouge
    'MEDIUM_URGENCY': '#ffc107',     # Jaune
    'LOW_URGENCY': '#28a745'         # Vert
}
