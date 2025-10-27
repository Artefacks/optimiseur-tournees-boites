#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de test pour vérifier que l'application fonctionne correctement.
"""

import sys
import os
from box_collection_optimizer import BoxCollectionOptimizer

def test_optimizer():
    """Teste les fonctionnalités de base de l'optimiseur."""
    print("Test de l'optimiseur...")
    
    try:
        # Test d'initialisation
        optimizer = BoxCollectionOptimizer('ml_boxes_ready.csv')
        print("[OK] Initialisation reussie")
        
        # Test de chargement d'état
        optimizer.load_state()
        print("[OK] Chargement d'etat reussi")
        
        # Test de calcul de score
        test_box_id = optimizer.df['n_boite'].iloc[0]
        score = optimizer.calculate_profitability_score(test_box_id)
        print(f"[OK] Calcul de score reussi: {score:.1f}")
        
        # Test de recommandations
        recommendations = optimizer.get_recommended_boxes(max_boxes=5, min_score=30.0)
        print(f"[OK] Generation de recommandations reussie: {len(recommendations)} boites")
        
        # Test de détails de boîte
        details = optimizer.get_box_details(test_box_id)
        if details:
            print("[OK] Recuperation des details de boite reussie")
        else:
            print("[ERREUR] Details de boite non trouves")
            return False
        
        # Test de marquage de visite
        optimizer.mark_visit(test_box_id, 7.5)
        print("[OK] Marquage de visite reussi")
        
        # Test de sauvegarde
        optimizer.save_state()
        print("[OK] Sauvegarde d'etat reussie")
        
        return True
        
    except Exception as e:
        print(f"[ERREUR] {e}")
        return False

def test_data_integrity():
    """Teste l'intégrité des données."""
    print("\nTest d'intégrité des données...")
    
    try:
        optimizer = BoxCollectionOptimizer('ml_boxes_ready.csv')
        
        # Vérifie que le fichier CSV est valide
        if optimizer.df.empty:
            print("[ERREUR] Fichier CSV vide")
            return False
        
        # Vérifie les colonnes nécessaires
        required_columns = ['n_boite', 'adresse', 'commune', 'cp', 'conteneur', 'volume_moyen']
        missing_columns = [col for col in required_columns if col not in optimizer.df.columns]
        
        if missing_columns:
            print(f"[ERREUR] Colonnes manquantes: {missing_columns}")
            return False
        
        # Vérifie les colonnes de semaines
        week_columns = [col for col in optimizer.df.columns if col.startswith('semaine_')]
        if len(week_columns) < 10:
            print(f"[ERREUR] Pas assez de colonnes de semaines: {len(week_columns)}")
            return False
        
        print(f"[OK] Donnees valides: {len(optimizer.df)} boites, {len(week_columns)} semaines")
        return True
        
    except Exception as e:
        print(f"[ERREUR] {e}")
        return False

def test_scoring_algorithm():
    """Teste l'algorithme de scoring."""
    print("\nTest de l'algorithme de scoring...")
    
    try:
        optimizer = BoxCollectionOptimizer('ml_boxes_ready.csv')
        optimizer.load_state()
        
        # Test avec différentes boîtes
        test_boxes = optimizer.df['n_boite'].head(5).tolist()
        
        for box_id in test_boxes:
            score = optimizer.calculate_profitability_score(box_id)
            expected_fill = optimizer.calculate_expected_fill(box_id)
            days_since = optimizer.calculate_days_since_last_visit(box_id)
            
            # Vérifie que les scores sont dans des plages raisonnables
            if not (0 <= score <= 100):
                print(f"[ERREUR] Score invalide pour boite {box_id}: {score}")
                return False
            
            if not (0 <= expected_fill <= 10):
                print(f"[ERREUR] Remplissage attendu invalide pour boite {box_id}: {expected_fill}")
                return False
            
            if days_since < 0:
                print(f"[ERREUR] Jours depuis derniere visite invalide pour boite {box_id}: {days_since}")
                return False
        
        print("[OK] Algorithme de scoring valide")
        return True
        
    except Exception as e:
        print(f"[ERREUR] {e}")
        return False

def main():
    """Fonction principale de test."""
    print("=== TEST DE L'APPLICATION OPTIMISEUR DE TOURNEES ===\n")
    
    # Vérifie que le fichier CSV existe
    if not os.path.exists('ml_boxes_ready.csv'):
        print("[ERREUR] Fichier 'ml_boxes_ready.csv' non trouve")
        print("Assurez-vous que le fichier de données est dans le même dossier que ce script")
        return False
    
    # Exécute les tests
    tests = [
        test_data_integrity,
        test_optimizer,
        test_scoring_algorithm
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
        print()
    
    # Résumé
    print("=== RESUME DES TESTS ===")
    print(f"Tests réussis: {passed}/{total}")
    
    if passed == total:
        print("[OK] Tous les tests sont passes avec succes!")
        print("\nL'application est prête à être utilisée.")
        print("Pour démarrer l'interface web: python app.py")
        return True
    else:
        print("[ERREUR] Certains tests ont echoue.")
        print("Vérifiez les erreurs ci-dessus avant d'utiliser l'application.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
