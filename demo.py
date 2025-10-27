#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de démonstration pour l'optimiseur de tournées de boîtes à habits.
Montre comment utiliser l'API et simule des visites.
"""

from box_collection_optimizer import BoxCollectionOptimizer
import time
import random

def main():
    print("=== DEMONSTRATION DE L'OPTIMISEUR DE TOURNEES ===\n")
    
    # Initialise l'optimiseur
    print("1. Initialisation de l'optimiseur...")
    optimizer = BoxCollectionOptimizer('ml_boxes_ready.csv')
    optimizer.load_state()
    print("   [OK] Optimiseur initialise avec succes\n")
    
    # Affiche les statistiques initiales
    print("2. Statistiques initiales:")
    total_boxes = len(optimizer.df)
    visited_boxes = len(optimizer.last_visit)
    print(f"   - Total des boîtes: {total_boxes}")
    print(f"   - Boîtes déjà visitées: {visited_boxes}")
    print(f"   - Taux de visite: {(visited_boxes/total_boxes)*100:.1f}%\n")
    
    # Récupère les recommandations
    print("3. Récupération des recommandations...")
    recommendations = optimizer.get_recommended_boxes(max_boxes=10, min_score=50.0)
    print(f"   [OK] {len(recommendations)} boites recommandees trouvees\n")
    
    # Affiche les top 5 recommandations
    print("4. TOP 5 des boîtes recommandées:")
    for i, box in enumerate(recommendations[:5], 1):
        print(f"   {i}. Boîte #{box['box_id']:3d} - Score: {box['profitability_score']:5.1f}")
        print(f"      Adresse: {box['address']}")
        print(f"      Remplissage attendu: {box['expected_fill']:4.1f}/10")
        print(f"      Dernière visite: {box['days_since_last_visit']} jours")
        print()
    
    # Simule quelques visites
    print("5. Simulation de visites...")
    boxes_to_visit = recommendations[:3]  # Visite les 3 premières boîtes
    
    for i, box in enumerate(boxes_to_visit, 1):
        box_id = box['box_id']
        print(f"   Visite {i}: Boîte #{box_id}")
        
        # Simule un niveau de remplissage observé (proche de l'attendu + variation)
        expected = box['expected_fill']
        observed = max(0, min(10, expected + random.uniform(-2, 2)))
        
        print(f"      Remplissage attendu: {expected:.1f}/10")
        print(f"      Remplissage observé: {observed:.1f}/10")
        
        # Marque la visite
        optimizer.mark_visit(box_id, observed)
        print(f"      [OK] Visite enregistree")
        
        # Affiche les détails de la boîte
        details = optimizer.get_box_details(box_id)
        if details:
            print(f"      Score actuel: {details['current_score']:.1f}")
            print(f"      Dernière visite: {details['days_since_last_visit']} jours")
        print()
        
        # Pause pour l'effet dramatique
        time.sleep(1)
    
    # Sauvegarde l'état
    print("6. Sauvegarde de l'état...")
    optimizer.save_state()
    print("   [OK] Etat sauvegarde dans 'optimizer_state.json'\n")
    
    # Affiche les nouvelles recommandations
    print("7. Nouvelles recommandations après les visites:")
    new_recommendations = optimizer.get_recommended_boxes(max_boxes=5, min_score=50.0)
    
    for i, box in enumerate(new_recommendations[:5], 1):
        print(f"   {i}. Boîte #{box['box_id']:3d} - Score: {box['profitability_score']:5.1f}")
        print(f"      Adresse: {box['address']}")
        print(f"      Remplissage attendu: {box['expected_fill']:4.1f}/10")
        print(f"      Dernière visite: {box['days_since_last_visit']} jours")
        print()
    
    # Statistiques finales
    print("8. Statistiques finales:")
    final_visited = len(optimizer.last_visit)
    print(f"   - Boîtes visitées: {final_visited} (+{final_visited - visited_boxes})")
    print(f"   - Taux de visite: {(final_visited/total_boxes)*100:.1f}%")
    
    # Analyse des performances
    print("\n9. Analyse des performances:")
    print("   - Les boîtes visitées ont maintenant un score d'urgence réduit")
    print("   - Le système a appris des niveaux de remplissage observés")
    print("   - Les nouvelles recommandations sont basées sur les données mises à jour")
    
    print("\n=== DEMONSTRATION TERMINEE ===")
    print("\nPour utiliser l'interface web:")
    print("1. Lancez: python app.py")
    print("2. Ouvrez: http://localhost:5000")
    print("3. Consultez les recommandations et marquez vos visites")

if __name__ == "__main__":
    main()
