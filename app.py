from flask import Flask, render_template, request, jsonify
import pandas as pd
from box_collection_optimizer import BoxCollectionOptimizer
import json
from datetime import datetime

app = Flask(__name__)

# Initialise l'optimiseur global
optimizer = None

def init_optimizer():
    global optimizer
    if optimizer is None:
        optimizer = BoxCollectionOptimizer('ml_boxes_ready.csv')
        optimizer.load_state()

@app.route('/')
def index():
    """Page d'accueil de l'application."""
    init_optimizer()
    return render_template('index.html')

@app.route('/api/recommendations')
def get_recommendations():
    """API pour récupérer les recommandations de boîtes."""
    init_optimizer()
    
    max_boxes = request.args.get('max_boxes', 20, type=int)
    min_score = request.args.get('min_score', 30.0, type=float)
    
    recommendations = optimizer.get_recommended_boxes(max_boxes, min_score)
    
    return jsonify({
        'success': True,
        'recommendations': recommendations,
        'total_boxes': len(optimizer.df),
        'timestamp': datetime.now().isoformat()
    })

@app.route('/api/box/<int:box_id>')
def get_box_details(box_id):
    """API pour récupérer les détails d'une boîte spécifique."""
    init_optimizer()
    
    details = optimizer.get_box_details(box_id)
    if details is None:
        return jsonify({'success': False, 'error': 'Boîte non trouvée'}), 404
    
    return jsonify({
        'success': True,
        'box': details
    })

@app.route('/api/visit', methods=['POST'])
def mark_visit():
    """API pour marquer une boîte comme visitée."""
    init_optimizer()
    
    data = request.get_json()
    box_id = data.get('box_id')
    fill_level = data.get('fill_level')
    
    if box_id is None:
        return jsonify({'success': False, 'error': 'ID de boîte requis'}), 400
    
    try:
        optimizer.mark_visit(box_id, fill_level)
        optimizer.save_state()
        
        return jsonify({
            'success': True,
            'message': f'Visite de la boîte #{box_id} enregistrée'
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/all-boxes')
def get_all_boxes():
    """Récupère toutes les boîtes avec leurs informations."""
    init_optimizer()
    
    try:
        search = request.args.get('search', '', type=str).lower()
        
        all_boxes = []
        for _, row in optimizer.df.iterrows():
            box_id = int(row['n_boite'])
            address = str(row['adresse'])
            commune = str(row['commune'])
            
            # Filtre par recherche si spécifié
            if search and search not in address.lower() and search not in str(box_id):
                continue
                
            box_info = {
                'box_id': box_id,
                'address': address,
                'commune': commune,
                'postal_code': str(row['cp']),
                'container_type': str(row['conteneur']),
                'average_fill': float(row['volume_moyen']),
                'profitability_score': optimizer.calculate_profitability_score(box_id),
                'expected_fill': optimizer.calculate_expected_fill(box_id),
                'days_since_last_visit': optimizer.calculate_days_since_last_visit(box_id)
            }
            all_boxes.append(box_info)
        
        # Trier par score de rentabilité décroissant
        all_boxes.sort(key=lambda x: x['profitability_score'], reverse=True)
        
        return jsonify({
            'success': True,
            'boxes': all_boxes,
            'total': len(all_boxes)
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/visited-boxes')
def get_visited_boxes():
    """Récupère les boîtes récemment visitées."""
    init_optimizer()
    
    try:
        visited_boxes = []
        for box_id, last_visit_date in optimizer.last_visit.items():
            box_data = optimizer.df[optimizer.df['n_boite'] == box_id]
            if not box_data.empty:
                row = box_data.iloc[0]
                days_since = (datetime.now() - last_visit_date).days
                
                box_info = {
                    'box_id': int(box_id),
                    'address': str(row['adresse']),
                    'commune': str(row['commune']),
                    'postal_code': str(row['cp']),
                    'container_type': str(row['conteneur']),
                    'last_visit_date': last_visit_date.isoformat(),
                    'days_since_last_visit': days_since,
                    'visit_history': optimizer.visit_history.get(box_id, [])
                }
                visited_boxes.append(box_info)
        
        # Trier par date de visite décroissante
        visited_boxes.sort(key=lambda x: x['last_visit_date'], reverse=True)
        
        return jsonify({
            'success': True,
            'visited_boxes': visited_boxes,
            'total': len(visited_boxes)
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/stats')
def get_stats():
    """API pour récupérer les statistiques générales."""
    init_optimizer()
    
    total_boxes = len(optimizer.df)
    visited_boxes = len(optimizer.last_visit)
    
    # Calcule les statistiques de remplissage
    avg_fills = optimizer.df['volume_moyen'].dropna()
    avg_fill = avg_fills.mean() if not avg_fills.empty else 0
    
    # Boîtes les plus performantes
    top_boxes = optimizer.df.nlargest(5, 'volume_moyen')[['n_boite', 'adresse', 'volume_moyen']].to_dict('records')
    
    return jsonify({
        'success': True,
        'stats': {
            'total_boxes': total_boxes,
            'visited_boxes': visited_boxes,
            'visit_rate': round((visited_boxes / total_boxes) * 100, 1) if total_boxes > 0 else 0,
            'average_fill': round(avg_fill, 1),
            'top_boxes': top_boxes
        }
    })

@app.route('/api/reset-visits', methods=['POST'])
def reset_visits():
    """API pour supprimer toutes les visites."""
    init_optimizer()
    
    try:
        # Compter les visites avant suppression
        visited_count = len(optimizer.last_visit)
        
        # Supprimer toutes les visites
        optimizer.last_visit = {}
        optimizer.visit_history = {}
        
        # Invalider le cache pour recalculer les scores
        optimizer.invalidate_cache()
        
        # Sauvegarder l'état
        optimizer.save_state()
        
        return jsonify({
            'success': True,
            'message': f'{visited_count} visites supprimées avec succès',
            'visited_count': visited_count
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/add-box', methods=['POST'])
def add_box():
    """API pour ajouter une nouvelle boîte."""
    init_optimizer()
    
    try:
        data = request.get_json()
        
        # Validation des champs requis
        required_fields = ['n_boite', 'adresse', 'commune', 'cp', 'conteneur', 'volume_moyen']
        missing_fields = [field for field in required_fields if field not in data]
        
        if missing_fields:
            return jsonify({
                'success': False, 
                'error': f'Champs manquants: {", ".join(missing_fields)}'
            }), 400
        
        # Ajouter la boîte
        success = optimizer.add_box(data)
        
        if success:
            # Sauvegarder l'état
            optimizer.save_state()
            
            return jsonify({
                'success': True,
                'message': f'Boîte #{data["n_boite"]} ajoutée avec succès',
                'box_id': data['n_boite']
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Erreur lors de l\'ajout de la boîte'
            }), 500
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/remove-box/<int:box_id>', methods=['DELETE'])
def remove_box(box_id):
    """API pour supprimer une boîte."""
    init_optimizer()
    
    try:
        success = optimizer.remove_box(box_id)
        
        if success:
            # Sauvegarder l'état
            optimizer.save_state()
            
            return jsonify({
                'success': True,
                'message': f'Boîte #{box_id} supprimée avec succès',
                'box_id': box_id
            })
        else:
            return jsonify({
                'success': False,
                'error': f'Boîte #{box_id} non trouvée'
            }), 404
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/update-box/<int:box_id>', methods=['PUT'])
def update_box(box_id):
    """API pour mettre à jour une boîte."""
    init_optimizer()
    
    try:
        data = request.get_json()
        
        # Supprimer n_boite des données si présent (ne peut pas être modifié)
        if 'n_boite' in data:
            del data['n_boite']
        
        success = optimizer.update_box(box_id, data)
        
        if success:
            # Sauvegarder l'état
            optimizer.save_state()
            
            return jsonify({
                'success': True,
                'message': f'Boîte #{box_id} mise à jour avec succès',
                'box_id': box_id
            })
        else:
            return jsonify({
                'success': False,
                'error': f'Boîte #{box_id} non trouvée'
            }), 404
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/export-csv')
def export_csv():
    """API pour exporter les recommandations en CSV."""
    init_optimizer()
    
    try:
        # Récupérer les paramètres de filtrage
        max_boxes = request.args.get('max_boxes', 20, type=int)
        min_score = request.args.get('min_score', 30.0, type=float)
        
        # Obtenir les recommandations
        recommendations = optimizer.get_recommended_boxes(max_boxes, min_score)
        
        if not recommendations:
            return jsonify({
                'success': False,
                'error': 'Aucune recommandation à exporter'
            }), 400
        
        # Générer le fichier CSV
        filename = optimizer.export_recommendations_to_csv(recommendations)
        
        # Lire le fichier et le renvoyer
        from flask import send_file
        import os
        
        return send_file(
            filename,
            as_attachment=True,
            download_name=f'recommandations_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv',
            mimetype='text/csv'
        )
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=False, host='0.0.0.0', port=port)
