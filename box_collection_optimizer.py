import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import json
from typing import List, Dict, Tuple
import warnings
import logging
import pytz
warnings.filterwarnings('ignore')

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('optimizer.log'),
        logging.StreamHandler()
    ]
)

class BoxCollectionOptimizer:
    """
    Système d'optimisation pour les tournées de ramassage des boîtes à habits.
    Prend en compte l'historique de remplissage et la dernière visite pour prédire
    les boîtes les plus rentables à visiter.
    """
    
    def __init__(self, csv_file: str):
        """Initialise l'optimiseur avec les données des boîtes."""
        self.df = pd.read_csv(csv_file)
        
        # Validation des colonnes nécessaires
        required_columns = ['n_boite', 'adresse', 'commune', 'cp', 'conteneur', 'volume_moyen']
        missing_columns = [col for col in required_columns if col not in self.df.columns]
        if missing_columns:
            raise ValueError(f"Colonnes manquantes dans le fichier CSV: {missing_columns}")
        
        # Standardisation du type n_boite (tout en int)
        self.df['n_boite'] = self.df['n_boite'].astype(int)
        
        # Validation des colonnes de semaines
        self.week_columns = [col for col in self.df.columns if col.startswith('semaine_')]
        if not self.week_columns:
            raise ValueError("Aucune colonne de semaine trouvée dans le fichier CSV")
        
        # Vérification de la cohérence des types
        if not self.df['volume_moyen'].dtype in ['float64', 'int64']:
            try:
                self.df['volume_moyen'] = pd.to_numeric(self.df['volume_moyen'], errors='coerce')
            except:
                raise ValueError("Impossible de convertir 'volume_moyen' en numérique")
        
        self.last_visit = {}  # Dictionnaire pour tracker la dernière visite de chaque boîte
        self.visit_history = {}  # Historique des visites
        
        # Cache pour les calculs vectorisés
        self._score_cache = {}
        self._cache_valid = False
        
        # Configuration timezone
        self.timezone = pytz.timezone('Europe/Zurich')
        
        logging.info(f"Optimiseur initialisé avec {len(self.df)} boîtes et {len(self.week_columns)} semaines de données")
        
        # Log des paramètres pour auditabilité
        self._log_parameters()
        
        # Pré-calculer les scores pour toutes les boîtes
        self._precompute_all_scores()
    
    def _log_parameters(self):
        """Log les paramètres de configuration pour auditabilité."""
        logging.info("=== PARAMÈTRES DE CONFIGURATION ===")
        logging.info(f"Timezone: {self.timezone}")
        logging.info("Fenêtre d'historique: 4 dernières semaines")
        logging.info("Fonction logistique urgence: 10 / (1 + exp(-0.5 * (days - 7)))")
        logging.info("Point d'inflexion urgence: 7 jours")
        logging.info("Multiplicateur urgence: 1.0 à 1.5 (+50% max)")
        logging.info("Poids expected_fill: 0.7, volume_moyen: 0.3")
        logging.info("Bonus tendance max: +2.0 points")
        logging.info("Score urgence boîtes jamais visitées: volume_moyen * 0.8 (max 8)")
        logging.info("=====================================")
    
    
    def _precompute_all_scores(self):
        """Pré-calcule tous les scores pour optimiser les performances."""
        logging.info("Pré-calcul des scores pour toutes les boîtes...")
        
        current_week = self.get_current_week()
        
        for _, box in self.df.iterrows():
            box_id = box['n_boite']
            
            # Pré-calculer les composants
            fill_score = self.calculate_fill_score(box_id, current_week)
            urgency_score = self.calculate_urgency_score(box_id)
            equity_score = self.calculate_equity_score(box_id)
            expected_fill = self.calculate_expected_fill(box_id)
            profitability_score = self.calculate_profitability_score(box_id)
            
            self._score_cache[box_id] = {
                'fill_score': fill_score,
                'urgency_score': urgency_score,
                'equity_score': equity_score,
                'expected_fill': expected_fill,
                'profitability_score': profitability_score,
                'days_since_last_visit': self.calculate_days_since_last_visit(box_id)
            }
        
        self._cache_valid = True
        logging.info(f"Scores pré-calculés pour {len(self._score_cache)} boîtes")
    
    def invalidate_cache(self):
        """Invalide le cache des scores (à appeler après une visite)."""
        self._cache_valid = False
        self._score_cache = {}
    
    def _recalculate_box_scores(self, box_id: int):
        """Recalcule les scores pour une boîte spécifique après une visite."""
        current_week = self.get_current_week_for_box(box_id)
        
        # Recalculer les composants
        fill_score = self.calculate_fill_score(box_id, current_week)
        urgency_score = self.calculate_urgency_score(box_id)
        equity_score = self.calculate_equity_score(box_id)
        expected_fill = self.calculate_expected_fill(box_id)
        profitability_score = self.calculate_profitability_score(box_id)
        
        # Mettre à jour le cache
        self._score_cache[box_id] = {
            'fill_score': fill_score,
            'urgency_score': urgency_score,
            'equity_score': equity_score,
            'expected_fill': expected_fill,
            'profitability_score': profitability_score,
            'days_since_last_visit': self.calculate_days_since_last_visit(box_id)
        }
    
    def get_current_week(self) -> int:
        """
        Détermine la dernière semaine valable (non-NA) dans les données globalement.
        """
        # Parcourt les colonnes de droite à gauche pour trouver la dernière semaine avec des données
        for i in range(len(self.week_columns), 0, -1):
            week_col = f'semaine_{i}'
            if week_col in self.df.columns:
                # Vérifie si cette semaine a au moins une valeur non-NA
                if not self.df[week_col].isna().all():
                    return i
        return 1  # Fallback si aucune semaine valide trouvée
    
    def get_current_week_for_box(self, box_id: int) -> int:
        """
        Détermine la dernière semaine valable (non-NA) pour une boîte spécifique.
        CORRECTION: Calcul par boîte plutôt que global.
        """
        box_data = self.df[self.df['n_boite'] == box_id]
        if box_data.empty:
            return 1
            
        # Parcourt les colonnes de droite à gauche pour cette boîte spécifique
        for i in range(len(self.week_columns), 0, -1):
            week_col = f'semaine_{i}'
            if week_col in self.df.columns:
                score = box_data[week_col].iloc[0]
                if pd.notna(score):
                    return i
        return 1  # Fallback si aucune semaine valide trouvée pour cette boîte

    def calculate_fill_score(self, box_id: int, current_week: int = None) -> float:
        """
        Calcule un score de remplissage pour une boîte donnée.
        Prend en compte l'historique récent et la tendance.
        CORRECTION: Utilise la dernière semaine valable spécifique à la boîte.
        """
        box_data = self.df[self.df['n_boite'] == box_id]
        if box_data.empty:
            return 0.0
            
        # CORRECTION: Utilise la semaine spécifique à la boîte
        if current_week is None:
            current_week = self.get_current_week_for_box(box_id)
        
        # Score basé sur les 4 dernières semaines
        recent_weeks = min(4, current_week)
        recent_scores = []
        
        # CORRECTION: Parcourir du plus ancien au plus récent pour la tendance
        for i in range(recent_weeks):
            week_num = current_week - recent_weeks + 1 + i  # Semaine la plus ancienne + i
            week_col = f'semaine_{week_num}'
            if week_col in self.df.columns:
                score = box_data[week_col].iloc[0]
                if pd.notna(score):
                    recent_scores.append(score)
        
        if not recent_scores:
            return 0.0
            
        # Score moyen des dernières semaines
        avg_score = np.mean(recent_scores)
        
        # CORRECTION: Bonus pour la tendance croissante (du plus ancien au plus récent)
        if len(recent_scores) >= 2:
            # Maintenant l'ordre est correct: ancien -> récent
            trend = np.polyfit(range(len(recent_scores)), recent_scores, 1)[0]
            trend_bonus = min(trend * 0.5, 2.0)  # Bonus maximum de 2 points
        else:
            trend_bonus = 0
            
        return max(0, avg_score + trend_bonus)
    
    def calculate_days_since_last_visit(self, box_id: int) -> int:
        """Calcule le nombre de jours depuis la dernière visite."""
        if box_id not in self.last_visit:
            # Si jamais visitée, retourner None pour traitement spécial
            return None
        
        # Utiliser le timezone Europe/Zurich - CORRECTION: ne pas remplacer le tz si déjà aware
        now_zurich = datetime.now(self.timezone)
        last_visit = self.last_visit[box_id]
        
        # Si last_visit est déjà aware, l'utiliser tel quel
        if last_visit.tzinfo is not None:
            days_since = (now_zurich - last_visit).days
        else:
            # Si naïf, le convertir en aware avec le timezone local
            last_visit_aware = last_visit.replace(tzinfo=self.timezone)
            days_since = (now_zurich - last_visit_aware).days
        
        return days_since
    
    def calculate_urgency_score(self, box_id: int) -> float:
        """
        Calcule un score d'urgence basé sur le temps écoulé depuis la dernière visite.
        NOUVELLE APPROCHE: Fonction progressive (logistique) au lieu de paliers rigides.
        """
        days_since = self.calculate_days_since_last_visit(box_id)
        
        # Si jamais visitée, utiliser volume_moyen comme proxy
        if days_since is None:
            box_data = self.df[self.df['n_boite'] == box_id]
            if not box_data.empty and 'volume_moyen' in box_data.columns:
                avg_fill = box_data['volume_moyen'].iloc[0]
                if pd.notna(avg_fill) and avg_fill > 0:
                    # Urgence basée sur le volume moyen (plus la boîte est productive, plus elle est urgente)
                    return min(avg_fill * 0.8, 8.0)  # Maximum 8 pour les boîtes jamais visitées
            return 3.0  # Urgence modérée par défaut pour les boîtes jamais visitées
        
        # Fonction logistique progressive pour l'urgence
        # Plus les jours augmentent, plus l'urgence croît de manière progressive
        # Paramètres: plateau à 10, point d'inflexion à 7 jours, croissance douce
        urgency = 10 / (1 + np.exp(-0.5 * (days_since - 7)))
        
        # Ajustement pour les très courtes périodes (éviter l'urgence excessive)
        if days_since <= 1:
            urgency = max(urgency, 1.0)
        elif days_since <= 3:
            urgency = max(urgency, 2.0)
        
        return min(urgency, 10.0)  # Maximum 10
    
    def calculate_expected_fill(self, box_id: int) -> float:
        """
        Calcule le remplissage attendu d'une boîte en tenant compte de:
        - L'historique de remplissage
        - La moyenne générale de la boîte
        NOUVELLE APPROCHE: L'urgence n'influence plus expected_fill directement.
        """
        fill_score = self.calculate_fill_score(box_id)
        
        # Récupère la moyenne générale de la boîte
        box_data = self.df[self.df['n_boite'] == box_id]
        if not box_data.empty and 'volume_moyen' in box_data.columns:
            avg_fill = box_data['volume_moyen'].iloc[0]
            if pd.isna(avg_fill):
                avg_fill = 0
        else:
            avg_fill = 0
        
        # Calcul du remplissage attendu (sans influence de l'urgence)
        # Moyenne pondérée entre le score récent et la moyenne historique
        expected_fill = (fill_score * 0.7) + (avg_fill * 0.3)
        
        return min(expected_fill, 10.0)  # Maximum 10
    
    def calculate_equity_score(self, box_id: int) -> float:
        """
        Calcule un score d'équité pour éviter qu'une boîte soit toujours ignorée.
        Plus une boîte n'a pas été visitée récemment, plus son score d'équité augmente.
        """
        days_since = self.calculate_days_since_last_visit(box_id)
        
        # Si jamais visitée, score d'équité élevé
        if days_since is None:
            return 8.0
        
        # Score d'équité basé sur le temps écoulé depuis la dernière visite
        # Fonction logarithmique pour éviter l'explosion des scores
        if days_since <= 0:
            return 0.0
        elif days_since <= 7:
            return days_since * 0.5  # 0.5 à 3.5 points
        elif days_since <= 30:
            return 3.5 + (days_since - 7) * 0.2  # 3.5 à 8.1 points
        else:
            return min(8.0 + (days_since - 30) * 0.1, 15.0)  # Maximum 15 points

    def calculate_profitability_score(self, box_id: int) -> float:
        """
        Calcule un score de rentabilité global pour une boîte.
        NOUVELLE APPROCHE: L'urgence agit comme multiplicateur final.
        OPTIMISATION: Utilise le cache si disponible.
        INCLUSION: Facteur d'équité pour distribution équitable.
        """
        # Utiliser le cache si disponible
        if self._cache_valid and box_id in self._score_cache:
            return self._score_cache[box_id]['profitability_score']
        
        expected_fill = self.calculate_expected_fill(box_id)
        urgency = self.calculate_urgency_score(box_id)
        equity = self.calculate_equity_score(box_id)
        
        # Normalisation des composants sur [0,1]
        normalized_fill = expected_fill / 10.0  # expected_fill est sur [0,10]
        normalized_urgency = urgency / 10.0      # urgency est sur [0,10]
        normalized_equity = equity / 15.0       # equity est sur [0,15]
        
        # Score de base (0-100) basé sur le remplissage attendu
        base_score = normalized_fill * 100
        
        # CORRECTION: Application de l'urgence comme multiplicateur (1.0 à 1.5) - plafond +50%
        urgency_multiplier = 1.0 + (normalized_urgency * 0.5)  # [1.0, 1.5]
        
        # NOUVEAU: Ajout du score d'équité (0 à 30 points supplémentaires)
        equity_bonus = normalized_equity * 30
        
        # Score final avec multiplicateur d'urgence et bonus d'équité
        profitability = (base_score * urgency_multiplier) + equity_bonus
        
        return min(profitability, 130.0)  # Maximum 130 (100 + 30 d'équité)
    
    def get_scoring_formula_documentation(self) -> str:
        """
        Retourne la documentation de la formule de scoring pour transparence.
        """
        return """
        FORMULE DE SCORING DE RENTABILITÉ:
        
        1. FILL_SCORE (0-10):
           - Moyenne des 4 dernières semaines avec données
           - Bonus de tendance croissante (max +2 points)
           - Calculé du plus ancien au plus récent
        
        2. EXPECTED_FILL (0-10):
           - Moyenne pondérée: fill_score * 0.7 + volume_moyen * 0.3
           - Représente le remplissage attendu sans influence de l'urgence
        
        3. URGENCY_SCORE (0-10):
           - Fonction logistique progressive: 10 / (1 + exp(-0.5 * (days - 7)))
           - Pour boîtes jamais visitées: basé sur volume_moyen * 0.8 (max 8)
           - Point d'inflexion à 7 jours
        
        4. EQUITY_SCORE (0-15):
           - Score d'équité pour distribution équitable
           - Boîtes jamais visitées: 8.0 points
           - 0-7 jours: 0.5 * jours (0.5 à 3.5 points)
           - 8-30 jours: 3.5 + (jours-7) * 0.2 (3.5 à 8.1 points)
           - 30+ jours: 8.0 + (jours-30) * 0.1 (max 15 points)
        
        5. PROFITABILITY_SCORE (0-130):
           - Score de base = (expected_fill / 10) * 100
           - Multiplicateur d'urgence = 1.0 + (urgency / 10) * 0.5
           - Bonus d'équité = (equity / 15) * 30
           - Score final = (score_base * multiplicateur_urgence) + bonus_équité
           - Maximum: 130 points (100 + 30 d'équité)
        
        CORRECTIONS APPLIQUÉES:
        - Timezone Europe/Zurich uniforme partout
        - Calcul de semaine spécifique par boîte
        - Multiplicateur urgence plafonné à +50% (au lieu de +100%)
        - Cache optimisé avec recalcul immédiat après visite
        - Facteur d'équité pour éviter l'oubli de certaines boîtes
        """
    
    def get_recommended_boxes(self, max_boxes: int = 20, min_score: float = 30.0) -> List[Dict]:
        """
        Retourne la liste des boîtes recommandées pour la visite.
        NOUVEAU: Inclut le monitoring des performances.
        """
        recommendations = []
        all_scores = []
        
        for _, box in self.df.iterrows():
            box_id = box['n_boite']
            score = self.calculate_profitability_score(box_id)
            expected_fill = self.calculate_expected_fill(box_id)
            days_since = self.calculate_days_since_last_visit(box_id)
            
            all_scores.append(score)
            
            if score >= min_score:
                equity_score = self.calculate_equity_score(box_id)
                recommendations.append({
                    'box_id': int(box_id),
                    'address': box['adresse'],
                    'commune': box['commune'],
                    'postal_code': box['cp'],
                    'container_type': box['conteneur'],
                    'profitability_score': round(score, 1),
                    'expected_fill': round(expected_fill, 1),
                    'equity_score': round(equity_score, 1),
                    'days_since_last_visit': days_since,
                    'average_fill': round(box['volume_moyen'], 1) if pd.notna(box['volume_moyen']) else 0
                })
        
        # Trie par score de rentabilité décroissant
        recommendations.sort(key=lambda x: x['profitability_score'], reverse=True)
        
        # Monitoring et logging
        self._log_scoring_stats(all_scores, recommendations[:5])
        
        return recommendations[:max_boxes]
    
    def _log_scoring_stats(self, all_scores: List[float], top_5: List[Dict]):
        """Log les statistiques de scoring pour le monitoring."""
        if not all_scores:
            return
            
        mean_score = np.mean(all_scores)
        std_score = np.std(all_scores)
        scored_boxes = len([s for s in all_scores if s > 0])
        
        logging.info(f"SCORING STATS - Boîtes scorées: {scored_boxes}/{len(all_scores)}, "
                    f"Moyenne: {mean_score:.1f}, Écart-type: {std_score:.1f}")
        
        if top_5:
            logging.info("TOP-5 BOÎTES:")
            for i, box in enumerate(top_5, 1):
                logging.info(f"  {i}. Boîte #{box['box_id']} - Score: {box['profitability_score']} - "
                           f"{box['address']} ({box['commune']})")
    
    def mark_visit(self, box_id: int, fill_level: float = None):
        """
        Marque une boîte comme visitée avec le niveau de remplissage observé.
        NOUVEAU: Logging des visites et journal persistant.
        """
        expected_fill = self.calculate_expected_fill(box_id)
        # Utiliser le timezone Europe/Zurich pour les visites
        self.last_visit[box_id] = datetime.now(self.timezone)
        
        if box_id not in self.visit_history:
            self.visit_history[box_id] = []
        
        visit_record = {
            'date': datetime.now(self.timezone).isoformat(),
            'fill_level': fill_level,
            'expected_fill': expected_fill
        }
        
        self.visit_history[box_id].append(visit_record)
        
        # Logging de la visite
        logging.info(f"VISITE ENREGISTRÉE - Boîte #{box_id}: "
                    f"Attendu: {expected_fill:.1f}, Observé: {fill_level if fill_level is not None else 'N/A'}")
        
        # Invalider le cache car les scores ont changé
        self.invalidate_cache()
        
        # CORRECTION: Recalculer immédiatement les scores pour cette boîte
        self._recalculate_box_scores(box_id)
        
        # Sauvegarde dans le journal persistant
        self._log_visit_to_csv(box_id, fill_level, expected_fill)
    
    def _log_visit_to_csv(self, box_id: int, fill_level: float, expected_fill: float):
        """Sauvegarde la visite dans un journal CSV persistant."""
        import csv
        import os
        
        csv_file = 'visits_log.csv'
        file_exists = os.path.isfile(csv_file)
        
        # Récupérer les infos de la boîte
        box_data = self.df[self.df['n_boite'] == box_id]
        if box_data.empty:
            return
            
        box_info = box_data.iloc[0]
        
        with open(csv_file, 'a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            
            # Écrire l'en-tête si le fichier n'existe pas
            if not file_exists:
                writer.writerow([
                    'timestamp', 'box_id', 'address', 'commune', 'postal_code',
                    'container_type', 'expected_fill', 'observed_fill', 'fill_difference',
                    'days_since_last_visit', 'average_fill'
                ])
            
            # Calculer la différence
            fill_diff = fill_level - expected_fill if fill_level is not None else None
            
            writer.writerow([
                datetime.now(self.timezone).isoformat(),
                box_id,
                box_info['adresse'],
                box_info['commune'],
                box_info['cp'],
                box_info['conteneur'],
                round(expected_fill, 2),
                fill_level,
                round(fill_diff, 2) if fill_diff is not None else None,
                self.calculate_days_since_last_visit(box_id),
                round(box_info['volume_moyen'], 2) if pd.notna(box_info['volume_moyen']) else None
            ])
    
    def get_box_details(self, box_id: int) -> Dict:
        """Retourne les détails complets d'une boîte."""
        box_data = self.df[self.df['n_boite'] == box_id]
        if box_data.empty:
            return None
        
        box = box_data.iloc[0]
        
        # Historique des 8 dernières semaines
        recent_history = []
        for i in range(8):
            week_col = f'semaine_{len(self.week_columns) - i}'
            if week_col in self.df.columns:
                score = box[week_col]
                if pd.notna(score):
                    recent_history.append({
                        'week': f'Semaine {len(self.week_columns) - i}',
                        'fill_level': float(score)
                    })
        
        return {
            'box_id': int(box_id),
            'address': box['adresse'],
            'commune': box['commune'],
            'postal_code': box['cp'],
            'container_type': box['conteneur'],
            'average_fill': round(box['volume_moyen'], 1) if pd.notna(box['volume_moyen']) else 0,
            'current_score': round(self.calculate_profitability_score(box_id), 1),
            'expected_fill': round(self.calculate_expected_fill(box_id), 1),
            'days_since_last_visit': self.calculate_days_since_last_visit(box_id),
            'recent_history': recent_history,
            'visit_history': self.visit_history.get(box_id, [])
        }
    
    def save_state(self, filename: str = 'optimizer_state.json'):
        """Sauvegarde l'état de l'optimiseur avec gestion timezone."""
        state = {
            'last_visit': {
                str(k): v.isoformat() if v.tzinfo is not None else v.replace(tzinfo=self.timezone).isoformat()
                for k, v in self.last_visit.items()
            },
            'visit_history': {str(k): v for k, v in self.visit_history.items()}
        }
        
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(state, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Erreur lors de la sauvegarde: {e}")
    
    def load_state(self, filename: str = 'optimizer_state.json'):
        """Charge l'état de l'optimiseur avec gestion timezone."""
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                state = json.load(f)
            
            self.last_visit = {}
            for k, v in state.get('last_visit', {}).items():
                # Charger en timezone aware
                dt = datetime.fromisoformat(v)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=self.timezone)
                self.last_visit[int(k)] = dt
                
            self.visit_history = {
                int(k): v for k, v in state.get('visit_history', {}).items()
            }
        except FileNotFoundError:
            print(f"Fichier d'état {filename} non trouvé. Initialisation avec état vide.")
        except Exception as e:
            print(f"Erreur lors du chargement: {e}")
    
    def add_box(self, box_data: Dict) -> bool:
        """
        Ajoute une nouvelle boîte au système.
        
        Args:
            box_data: Dictionnaire contenant les données de la boîte
                     {'n_boite': int, 'adresse': str, 'commune': str, 'cp': str, 
                      'conteneur': str, 'volume_moyen': float}
        
        Returns:
            bool: True si l'ajout a réussi, False sinon
        """
        try:
            # Validation des données requises
            required_fields = ['n_boite', 'adresse', 'commune', 'cp', 'conteneur', 'volume_moyen']
            for field in required_fields:
                if field not in box_data:
                    logging.error(f"Champ requis manquant: {field}")
                    return False
            
            # Vérifier que la boîte n'existe pas déjà
            if box_data['n_boite'] in self.df['n_boite'].values:
                logging.error(f"Boîte #{box_data['n_boite']} existe déjà")
                return False
            
            # Créer une nouvelle ligne pour le DataFrame
            new_row = {
                'n_boite': int(box_data['n_boite']),
                'adresse': str(box_data['adresse']),
                'commune': str(box_data['commune']),
                'cp': str(box_data['cp']),
                'conteneur': str(box_data['conteneur']),
                'volume_moyen': float(box_data['volume_moyen'])
            }
            
            # Ajouter des colonnes de semaines vides (NA)
            for week_col in self.week_columns:
                new_row[week_col] = np.nan
            
            # Ajouter la nouvelle ligne au DataFrame
            new_df_row = pd.DataFrame([new_row])
            self.df = pd.concat([self.df, new_df_row], ignore_index=True)
            
            # Initialiser les données de visite pour cette boîte
            box_id = int(box_data['n_boite'])
            if box_id not in self.last_visit:
                self.last_visit[box_id] = None
            if box_id not in self.visit_history:
                self.visit_history[box_id] = []
            
            # Invalider le cache pour recalculer les scores
            self.invalidate_cache()
            
            logging.info(f"Boîte #{box_id} ajoutée avec succès: {box_data['adresse']}")
            return True
            
        except Exception as e:
            logging.error(f"Erreur lors de l'ajout de la boîte: {e}")
            return False
    
    def remove_box(self, box_id: int) -> bool:
        """
        Supprime une boîte du système.
        
        Args:
            box_id: ID de la boîte à supprimer
        
        Returns:
            bool: True si la suppression a réussi, False sinon
        """
        try:
            # Vérifier que la boîte existe
            if box_id not in self.df['n_boite'].values:
                logging.error(f"Boîte #{box_id} non trouvée")
                return False
            
            # Supprimer la boîte du DataFrame
            self.df = self.df[self.df['n_boite'] != box_id].reset_index(drop=True)
            
            # Supprimer les données de visite associées
            if box_id in self.last_visit:
                del self.last_visit[box_id]
            if box_id in self.visit_history:
                del self.visit_history[box_id]
            
            # Supprimer du cache si présent
            if box_id in self._score_cache:
                del self._score_cache[box_id]
            
            logging.info(f"Boîte #{box_id} supprimée avec succès")
            return True
            
        except Exception as e:
            logging.error(f"Erreur lors de la suppression de la boîte: {e}")
            return False
    
    def update_box(self, box_id: int, box_data: Dict) -> bool:
        """
        Met à jour les données d'une boîte existante.
        
        Args:
            box_id: ID de la boîte à mettre à jour
            box_data: Dictionnaire contenant les nouvelles données
        
        Returns:
            bool: True si la mise à jour a réussi, False sinon
        """
        try:
            # Vérifier que la boîte existe
            if box_id not in self.df['n_boite'].values:
                logging.error(f"Boîte #{box_id} non trouvée")
                return False
            
            # Mettre à jour les champs autorisés
            allowed_fields = ['adresse', 'commune', 'cp', 'conteneur', 'volume_moyen']
            for field in allowed_fields:
                if field in box_data:
                    self.df.loc[self.df['n_boite'] == box_id, field] = box_data[field]
            
            # Invalider le cache pour recalculer les scores
            self.invalidate_cache()
            
            logging.info(f"Boîte #{box_id} mise à jour avec succès")
            return True
            
        except Exception as e:
            logging.error(f"Erreur lors de la mise à jour de la boîte: {e}")
            return False
    
    def parse_address(self, address: str) -> Tuple[str, str]:
        """
        Décompose une adresse en rue et numéro.
        Gère les cas avec plusieurs adresses en prenant la première.
        
        Args:
            address: Adresse complète
        
        Returns:
            Tuple[str, str]: (rue, numéro)
        """
        if not address or pd.isna(address):
            return "", ""
        
        address = str(address).strip()
        
        # Gérer les cas avec plusieurs adresses (ex: "Chemin des Ouches 1 / Chemin des Sports")
        # Prendre seulement la première adresse
        if '/' in address:
            address = address.split('/')[0].strip()
        elif ' / ' in address:
            address = address.split(' / ')[0].strip()
        
        # Patterns courants pour extraire le numéro
        import re
        
        # Pattern 1: Numéro au début (ex: "123 Rue de la Paix")
        pattern1 = r'^(\d+[a-zA-Z]?)\s+(.+)$'
        match1 = re.match(pattern1, address)
        if match1:
            return match1.group(2).strip(), match1.group(1).strip()
        
        # Pattern 2: Numéro à la fin (ex: "Rue de la Paix 123")
        pattern2 = r'^(.+?)\s+(\d+[a-zA-Z]?)$'
        match2 = re.match(pattern2, address)
        if match2:
            return match2.group(1).strip(), match2.group(2).strip()
        
        # Pattern 3: Numéro avec virgule (ex: "Rue de la Paix, 123")
        pattern3 = r'^(.+?),\s*(\d+[a-zA-Z]?)$'
        match3 = re.match(pattern3, address)
        if match3:
            return match3.group(1).strip(), match3.group(2).strip()
        
        # Si aucun pattern ne correspond, retourner l'adresse complète comme rue
        return address, ""
    
    def generate_recommended_name(self, box_id: int, commune: str, container_type: str) -> str:
        """
        Génère un nom recommandé pour une boîte.
        
        Args:
            box_id: ID de la boîte
            commune: Commune de la boîte
            container_type: Type de conteneur
        
        Returns:
            str: Nom recommandé
        """
        # Générer un nom basé sur la commune et le type
        commune_clean = commune.replace(' ', '').replace('-', '').lower()
        container_clean = container_type.lower()
        
        # Créer un nom unique et descriptif
        recommended_name = f"Boite_{commune_clean}_{container_clean}_{box_id}"
        
        return recommended_name
    
    def export_recommendations_to_csv(self, recommendations: List[Dict], filename: str = None) -> str:
        """
        Exporte les recommandations vers un fichier CSV avec le format demandé.
        
        Args:
            recommendations: Liste des recommandations
            filename: Nom du fichier (optionnel)
        
        Returns:
            str: Chemin du fichier créé
        """
        import csv
        from datetime import datetime
        
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"recommandations_{timestamp}.csv"
        
        try:
            with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
                # En-têtes selon le format demandé
                fieldnames = [
                    'Numéro de client',
                    'Nom du client', 
                    'Rue et num',
                    'Code postal',
                    'Ville',
                    'Numéro de commande',
                    'Date de livraison',
                    'Remplissage attendu (%)',
                    'Revenu (EUR)'
                ]
                
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                
                # Générer un numéro de commande de base
                base_order_number = 10000
                
                for i, rec in enumerate(recommendations):
                    # Décomposer l'adresse
                    rue, numero = self.parse_address(rec['address'])
                    
                    # Générer le nom recommandé
                    box_data = self.df[self.df['n_boite'] == rec['box_id']]
                    container_type = box_data['conteneur'].iloc[0] if not box_data.empty else 'Textile'
                    recommended_name = self.generate_recommended_name(
                        rec['box_id'], rec['commune'], container_type
                    )
                    
                    # Formater l'adresse proprement
                    if numero and rue:
                        # Format: "avenue de la praille 47"
                        formatted_address = f"{rue.lower()} {numero}"
                    elif rue:
                        # Pas de numéro, juste la rue
                        formatted_address = rue.lower()
                    else:
                        # Fallback
                        formatted_address = rec['address'].lower() if rec['address'] else ""
                    
                    # Nettoyer le code postal (enlever .0 si présent)
                    postal_code = str(rec['postal_code']).replace('.0', '')
                    
                    # Créer la ligne CSV
                    remplissage_attendu = round(rec['expected_fill'] * 10, 1)  # % sur 100
                    revenu = round(180 * (rec['expected_fill']/10) * 0.2, 2)   # en €
                    row = {
                        'Numéro de client': f"GFL-C{rec['box_id']}",  # Format basé sur l'image
                        'Nom du client': recommended_name,
                        'Rue et num': formatted_address,
                        'Code postal': postal_code,
                        'Ville': rec['commune'],
                        'Numéro de commande': str(base_order_number + i),
                        'Date de livraison': datetime.now().strftime("%d/%m/%Y"),
                        'Remplissage attendu (%)': remplissage_attendu,
                        'Revenu (EUR)': revenu
                    }
                    
                    writer.writerow(row)
            
            logging.info(f"Export CSV créé: {filename} avec {len(recommendations)} recommandations")
            return filename
            
        except Exception as e:
            logging.error(f"Erreur lors de l'export CSV: {e}")
            raise e

def main():
    """Fonction principale pour tester l'optimiseur."""
    # Initialise l'optimiseur
    optimizer = BoxCollectionOptimizer('ml_boxes_ready.csv')
    
    # Charge l'état précédent s'il existe
    optimizer.load_state()
    
    print("=== OPTIMISEUR DE TOURNÉES DE RAMASSAGE ===\n")
    
    # Affiche les recommandations
    recommendations = optimizer.get_recommended_boxes(max_boxes=15, min_score=40.0)
    
    print(f"TOP {len(recommendations)} BOITES RECOMMANDEES POUR AUJOURD'HUI:\n")
    
    for i, box in enumerate(recommendations, 1):
        print(f"{i:2d}. Boîte #{box['box_id']:3d} - Score: {box['profitability_score']:5.1f}")
        print(f"    Adresse: {box['address']}")
        print(f"    Commune: {box['commune']} ({box['postal_code']})")
        print(f"    Remplissage attendu: {box['expected_fill']:4.1f}/10")
        print(f"    Derniere visite: {box['days_since_last_visit']} jours")
        print(f"    Moyenne historique: {box['average_fill']:4.1f}/10")
        print(f"    Type: {box['container_type']}")
        print()
    
    # Sauvegarde l'état
    optimizer.save_state()
    
    print("Etat sauvegarde dans 'optimizer_state.json'")
    print("\nCONSEILS D'UTILISATION:")
    print("   - Visitez d'abord les boites avec le score le plus eleve")
    print("   - Marquez les visites avec la commande: optimizer.mark_visit(box_id, fill_level)")
    print("   - Les boites non visites depuis longtemps ont une priorite elevee")
    print("   - Le systeme apprend de vos visites pour ameliorer les predictions")

if __name__ == "__main__":
    main()
