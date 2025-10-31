// Application JavaScript pour l'optimiseur de tournées

let currentBoxId = null;
let recommendations = [];

// Initialisation de l'application
document.addEventListener('DOMContentLoaded', function() {
    loadRecommendations();
    loadStats();
    loadCommunes();
    
    // Gestion des onglets
    const tabButtons = document.querySelectorAll('#mainTabs button[data-bs-toggle="tab"]');
    tabButtons.forEach(button => {
        button.addEventListener('shown.bs.tab', function(event) {
            const target = event.target.getAttribute('data-bs-target');
            if (target === '#all-boxes') {
                loadAllBoxes();
            } else if (target === '#visited') {
                loadVisitedBoxes();
            }
        });
    });
});

// Charge les recommandations
async function loadRecommendations() {
    const maxBoxes = document.getElementById('maxBoxes').value;
    const minScore = document.getElementById('minScore').value;
    
    try {
        const response = await fetch(`/api/recommendations?max_boxes=${maxBoxes}&min_score=${minScore}`);
        const data = await response.json();
        
        if (data.success) {
            recommendations = data.recommendations;
            displayRecommendations(recommendations);
            updateQuickStats(data);
        } else {
            showError('Erreur lors du chargement des recommandations');
        }
    } catch (error) {
        console.error('Erreur:', error);
        showError('Erreur de connexion au serveur');
    }
}

// Affiche les recommandations
function displayRecommendations(boxes) {
    const container = document.getElementById('recommendationsList');
    const loadingSpinner = document.getElementById('loadingSpinner');
    
    loadingSpinner.style.display = 'none';
    
    if (boxes.length === 0) {
        container.innerHTML = `
            <div class="alert alert-info-custom alert-custom">
                <i class="fas fa-info-circle me-2"></i>
                Aucune boîte ne correspond aux critères sélectionnés.
            </div>
        `;
        return;
    }
    
    container.innerHTML = boxes.map((box, index) => createBoxCard(box, index + 1)).join('');
    document.getElementById('recommendationCount').textContent = `${boxes.length} boîtes`;
}

// Crée une carte pour une boîte
function createBoxCard(box, rank) {
    const scoreClass = getScoreClass(box.profitability_score);
    const urgencyClass = getUrgencyClass(box.days_since_last_visit);
    const urgencyText = getUrgencyText(box.days_since_last_visit);
    
    return `
        <div class="box-item" onclick="showBoxDetails(${box.box_id})">
            <div class="box-header">
                <div>
                    <h6 class="mb-1">#${rank} - Boîte ${box.box_id}</h6>
                    <div class="address-text">${box.address}</div>
                    <div class="address-text">${box.commune} (${box.postal_code})</div>
                </div>
                <div class="score-badge ${scoreClass}">
                    ${box.profitability_score}
                </div>
            </div>
            <div class="box-body">
                <div class="row">
                    <div class="col-md-6">
                        <div class="metric-item">
                            <span class="metric-label">
                                <span class="urgency-indicator ${urgencyClass}"></span>
                                Remplissage attendu
                            </span>
                            <span class="metric-value">${box.expected_fill}/10</span>
                        </div>
                        <div class="metric-item">
                            <span class="metric-label">Dernière visite</span>
                            <span class="metric-value">${box.days_since_last_visit} jours</span>
                        </div>
                        <div class="metric-item">
                            <span class="metric-label">Moyenne historique</span>
                            <span class="metric-value">${box.average_fill}/10</span>
                        </div>
                    </div>
                    <div class="col-md-6">
                        <div class="fill-bar">
                            <div class="fill-progress" style="width: ${(box.expected_fill / 10) * 100}%"></div>
                        </div>
                        <div class="metric-item">
                            <span class="metric-label">Type de conteneur</span>
                            <span class="metric-value">${box.container_type}</span>
                        </div>
                        <div class="metric-item">
                            <span class="metric-label">Urgence</span>
                            <span class="metric-value">${urgencyText}</span>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    `;
}

// Détermine la classe CSS pour le score
function getScoreClass(score) {
    if (score >= 80) return 'score-excellent';
    if (score >= 60) return 'score-good';
    if (score >= 40) return 'score-average';
    return 'score-poor';
}

// Détermine la classe CSS pour l'urgence
function getUrgencyClass(days) {
    if (days >= 14) return 'urgency-high';
    if (days >= 7) return 'urgency-medium';
    return 'urgency-low';
}

// Détermine le texte pour l'urgence
function getUrgencyText(days) {
    if (days >= 14) return 'Très élevée';
    if (days >= 7) return 'Élevée';
    if (days >= 3) return 'Moyenne';
    return 'Faible';
}

// Affiche les détails d'une boîte
async function showBoxDetails(boxId) {
    currentBoxId = boxId;
    
    try {
        const response = await fetch(`/api/box/${boxId}`);
        const data = await response.json();
        
        if (data.success) {
            displayBoxDetails(data.box);
            const modal = new bootstrap.Modal(document.getElementById('boxDetailsModal'));
            modal.show();
        } else {
            showError('Erreur lors du chargement des détails de la boîte');
        }
    } catch (error) {
        console.error('Erreur:', error);
        showError('Erreur de connexion au serveur');
    }
}

// Affiche les détails d'une boîte dans le modal
function displayBoxDetails(box) {
    const content = document.getElementById('boxDetailsContent');
    
    const historyChart = createHistoryChart(box.recent_history);
    
    content.innerHTML = `
        <div class="row">
            <div class="col-md-6">
                <h6 class="text-primary">Informations Générales</h6>
                <div class="metric-item">
                    <span class="metric-label">ID Boîte</span>
                    <span class="metric-value">${box.box_id}</span>
                </div>
                <div class="metric-item">
                    <span class="metric-label">Adresse</span>
                    <span class="metric-value">${box.address}</span>
                </div>
                <div class="metric-item">
                    <span class="metric-label">Commune</span>
                    <span class="metric-value">${box.commune} (${box.postal_code})</span>
                </div>
                <div class="metric-item">
                    <span class="metric-label">Type</span>
                    <span class="metric-value">${box.container_type}</span>
                </div>
            </div>
            <div class="col-md-6">
                <h6 class="text-primary">Métriques</h6>
                <div class="metric-item">
                    <span class="metric-label">Score de rentabilité</span>
                    <span class="metric-value">${box.current_score}</span>
                </div>
                <div class="metric-item">
                    <span class="metric-label">Remplissage attendu</span>
                    <span class="metric-value">${box.expected_fill}/10</span>
                </div>
                <div class="metric-item">
                    <span class="metric-label">Moyenne historique</span>
                    <span class="metric-value">${box.average_fill}/10</span>
                </div>
                <div class="metric-item">
                    <span class="metric-label">Dernière visite</span>
                    <span class="metric-value">${box.days_since_last_visit} jours</span>
                </div>
            </div>
        </div>
        
        <div class="history-chart">
            <h6 class="text-primary mb-3">Historique des 8 dernières semaines</h6>
            ${historyChart}
        </div>
        
        <div class="visit-form" id="visitForm" style="display: none;">
            <h6 class="text-success mb-3">Enregistrer la visite</h6>
            <div class="row">
                <div class="col-md-6">
                    <label for="fillLevel" class="form-label">Niveau de remplissage observé (0-10)</label>
                    <input type="number" class="form-control" id="fillLevel" min="0" max="10" step="0.1" placeholder="Ex: 7.5">
                </div>
                <div class="col-md-6 d-flex align-items-end">
                    <button class="btn btn-success w-100" onclick="confirmVisit()">
                        <i class="fas fa-check me-2"></i>Confirmer la visite
                    </button>
                </div>
            </div>
        </div>
    `;
}

// Crée un graphique simple de l'historique
function createHistoryChart(history) {
    if (!history || history.length === 0) {
        return '<p class="text-muted">Aucun historique disponible</p>';
    }
    
    const maxValue = Math.max(...history.map(h => h.fill_level));
    const chartHeight = 150;
    
    const bars = history.map((h, index) => {
        const height = (h.fill_level / maxValue) * chartHeight;
        const color = h.fill_level >= 7 ? '#28a745' : h.fill_level >= 4 ? '#ffc107' : '#dc3545';
        
        return `
            <div class="d-flex flex-column align-items-center me-2" style="width: 40px;">
                <div class="bg-light border rounded" style="height: ${chartHeight}px; width: 30px; position: relative;">
                    <div style="
                        background-color: ${color};
                        height: ${height}px;
                        width: 100%;
                        position: absolute;
                        bottom: 0;
                        border-radius: 0 0 4px 4px;
                    "></div>
                </div>
                <small class="mt-1 text-muted">${h.week.split(' ')[1]}</small>
                <small class="text-primary fw-bold">${h.fill_level}</small>
            </div>
        `;
    }).join('');
    
    return `
        <div class="d-flex align-items-end justify-content-center" style="height: ${chartHeight + 50}px;">
            ${bars}
        </div>
    `;
}

// Marque une boîte comme visitée
function markAsVisited() {
    document.getElementById('visitForm').style.display = 'block';
}

// Confirme la visite
async function confirmVisit() {
    const fillLevel = document.getElementById('fillLevel').value;
    
    if (!fillLevel || fillLevel < 0 || fillLevel > 10) {
        showError('Veuillez entrer un niveau de remplissage valide (0-10)');
        return;
    }
    
    try {
        const response = await fetch('/api/visit', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                box_id: currentBoxId,
                fill_level: parseFloat(fillLevel)
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            showSuccess('Visite enregistrée avec succès !');
            const modal = bootstrap.Modal.getInstance(document.getElementById('boxDetailsModal'));
            modal.hide();
            loadRecommendations(); // Recharge les recommandations
        } else {
            showError(data.error || 'Erreur lors de l\'enregistrement de la visite');
        }
    } catch (error) {
        console.error('Erreur:', error);
        showError('Erreur de connexion au serveur');
    }
}

// Applique les filtres
function applyFilters() {
    loadRecommendations();
}

// Actualise les données
function refreshData() {
    loadRecommendations();
    loadStats();
}

// Supprime toutes les visites
async function resetVisits() {
    // Confirmation avant suppression
    const confirmed = confirm('Êtes-vous sûr de vouloir supprimer toutes les visites ? Cette action est irréversible.');
    if (!confirmed) {
        return;
    }
    
    try {
        const response = await fetch('/api/reset-visits', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            }
        });
        
        const data = await response.json();
        
        if (data.success) {
            // Afficher le message de succès
            showSuccess(data.message);
            
            // Actualiser toutes les données
            loadRecommendations();
            loadStats();
            loadVisitedBoxes();
            
            // Si on est sur l'onglet des boîtes visitées, le vider
            const visitedContainer = document.getElementById('visitedBoxesList');
            if (visitedContainer) {
                visitedContainer.innerHTML = '<div class="alert alert-info">Aucune boîte visitée récemment.</div>';
            }
        } else {
            showError('Erreur lors de la suppression des visites: ' + data.error);
        }
    } catch (error) {
        console.error('Erreur:', error);
        showError('Erreur de connexion au serveur');
    }
}

// Charge les statistiques
async function loadStats() {
    try {
        const response = await fetch('/api/stats');
        const data = await response.json();
        
        if (data.success) {
            updateQuickStats(data);
        }
    } catch (error) {
        console.error('Erreur lors du chargement des statistiques:', error);
    }
}

// Met à jour les statistiques rapides
function updateQuickStats(data) {
    if (data.stats) {
        document.getElementById('totalBoxes').textContent = data.stats.total_boxes;
        document.getElementById('visitedBoxes').textContent = data.stats.visited_boxes;
        document.getElementById('visitRate').textContent = data.stats.visit_rate + '%';
        document.getElementById('avgFill').textContent = data.stats.average_fill;
        document.getElementById('quickStats').style.display = 'block';
    }
}

// Affiche les statistiques détaillées
async function showStats() {
    try {
        const response = await fetch('/api/stats');
        const data = await response.json();
        
        if (data.success) {
            displayStats(data.stats);
            const modal = new bootstrap.Modal(document.getElementById('statsModal'));
            modal.show();
        }
    } catch (error) {
        console.error('Erreur:', error);
        showError('Erreur lors du chargement des statistiques');
    }
}

// Affiche les statistiques dans le modal
function displayStats(stats) {
    const content = document.getElementById('statsContent');
    
    const topBoxesHtml = stats.top_boxes.map(box => `
        <tr>
            <td>${box.n_boite}</td>
            <td>${box.adresse}</td>
            <td><span class="badge bg-primary">${box.volume_moyen.toFixed(1)}/10</span></td>
        </tr>
    `).join('');
    
    content.innerHTML = `
        <div class="row">
            <div class="col-md-6">
                <div class="stats-card">
                    <h5>Total des Boîtes</h5>
                    <h3 class="text-primary">${stats.total_boxes}</h3>
                </div>
            </div>
            <div class="col-md-6">
                <div class="stats-card">
                    <h5>Boîtes Visitées</h5>
                    <h3 class="text-success">${stats.visited_boxes}</h3>
                </div>
            </div>
        </div>
        
        <div class="row mt-4">
            <div class="col-md-6">
                <div class="stats-card">
                    <h5>Taux de Visite</h5>
                    <h3 class="text-info">${stats.visit_rate}%</h3>
                </div>
            </div>
            <div class="col-md-6">
                <div class="stats-card">
                    <h5>Remplissage Moyen</h5>
                    <h3 class="text-warning">${stats.average_fill}/10</h3>
                </div>
            </div>
        </div>
        
        <div class="row mt-4">
            <div class="col-md-12">
                <div class="card">
                    <div class="card-header">
                        <h5 class="mb-0">Top 5 des Boîtes les Plus Performantes</h5>
                    </div>
                    <div class="card-body">
                        <div class="table-responsive">
                            <table class="table table-striped">
                                <thead>
                                    <tr>
                                        <th>ID Boîte</th>
                                        <th>Adresse</th>
                                        <th>Remplissage Moyen</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    ${topBoxesHtml}
                                </tbody>
                            </table>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    `;
}

// Charge toutes les boîtes
async function loadAllBoxes() {
    const searchTerm = document.getElementById('searchBox').value;
    
    try {
        const response = await fetch(`/api/all-boxes?search=${encodeURIComponent(searchTerm)}`);
        const data = await response.json();
        
        if (data.success) {
            displayAllBoxes(data.boxes);
        } else {
            showError('Erreur lors du chargement des boîtes');
        }
    } catch (error) {
        console.error('Erreur:', error);
        showError('Erreur de connexion au serveur');
    }
}

// Affiche toutes les boîtes
function displayAllBoxes(boxes) {
    const container = document.getElementById('allBoxesList');
    
    if (boxes.length === 0) {
        container.innerHTML = `
            <div class="alert alert-info">
                <i class="fas fa-info-circle me-2"></i>
                Aucune boîte trouvée.
            </div>
        `;
        return;
    }
    
    container.innerHTML = boxes.map((box, index) => createBoxCard(box, index + 1)).join('');
}

// Charge les boîtes visitées
async function loadVisitedBoxes() {
    try {
        const response = await fetch('/api/visited-boxes');
        const data = await response.json();
        
        if (data.success) {
            displayVisitedBoxes(data.visited_boxes);
        } else {
            showError('Erreur lors du chargement des visites');
        }
    } catch (error) {
        console.error('Erreur:', error);
        showError('Erreur de connexion au serveur');
    }
}

// Affiche les boîtes visitées
function displayVisitedBoxes(boxes) {
    const container = document.getElementById('visitedBoxesList');
    
    if (boxes.length === 0) {
        container.innerHTML = `
            <div class="alert alert-info">
                <i class="fas fa-info-circle me-2"></i>
                Aucune visite enregistrée.
            </div>
        `;
        return;
    }
    
    container.innerHTML = boxes.map(box => createVisitedBoxCard(box)).join('');
}

// Crée une carte pour une boîte visitée
function createVisitedBoxCard(box) {
    const visitDate = new Date(box.last_visit_date).toLocaleDateString('fr-FR');
    const urgencyClass = getUrgencyClass(box.days_since_last_visit);
    
    return `
        <div class="box-item visited-box" onclick="showBoxDetails(${box.box_id})">
            <div class="box-header">
                <div>
                    <h6 class="mb-1">Boîte ${box.box_id}</h6>
                    <div class="address-text">${box.address}</div>
                    <div class="address-text">${box.commune} (${box.postal_code})</div>
                </div>
                <div class="visit-info">
                    <span class="badge bg-success">Visité</span>
                </div>
            </div>
            <div class="box-body">
                <div class="row">
                    <div class="col-md-6">
                        <div class="metric-item">
                            <span class="metric-label">Dernière visite</span>
                            <span class="metric-value">${visitDate}</span>
                        </div>
                        <div class="metric-item">
                            <span class="metric-label">Il y a</span>
                            <span class="metric-value">${box.days_since_last_visit} jours</span>
                        </div>
                    </div>
                    <div class="col-md-6">
                        <div class="metric-item">
                            <span class="metric-label">Type</span>
                            <span class="metric-value">${box.container_type}</span>
                        </div>
                        <div class="metric-item">
                            <span class="metric-label">Historique</span>
                            <span class="metric-value">${box.visit_history.length} visites</span>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    `;
}

// Recherche dans les boîtes
function searchBoxes() {
    loadAllBoxes();
}

// Charge la liste des communes
async function loadCommunes() {
    // Cette fonction pourrait être implémentée pour charger dynamiquement les communes
    // Pour l'instant, on laisse vide car les communes sont déjà dans les données
}

// ===== EXPORT CSV =====

// Exporte les recommandations en CSV (avec validation et gestion d'erreur)
async function exportToCSV() {
    try {
        let maxBoxes = document.getElementById('maxBoxes').value;
        let minScore = document.getElementById('minScore').value;
        
        // Normaliser les entrées (gérer virgule décimale côté UI)
        if (typeof minScore === 'string') {
            minScore = minScore.replace(',', '.');
        }
        
        const params = new URLSearchParams({
            max_boxes: String(maxBoxes || '20'),
            min_score: String(minScore || '30')
        });
        
        const response = await fetch(`/api/export-csv?${params.toString()}`);
        
        if (!response.ok) {
            // Tenter de lire l'erreur JSON du backend
            let message = 'Erreur lors de l\'export CSV';
            try {
                const data = await response.json();
                if (data && data.error) message = data.error;
            } catch (_) {
                // ignorer si non JSON
            }
            showError(message);
            return;
        }
        
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `recommandations_${new Date().toISOString().slice(0,19).replace(/:/g, '-')}.csv`;
        document.body.appendChild(a);
        a.click();
        a.remove();
        window.URL.revokeObjectURL(url);
        
        showSuccess('Export CSV téléchargé.');
    } catch (error) {
        console.error('Erreur lors de l\'export:', error);
        showError('Erreur de connexion au serveur');
    }
}

// Affiche un message d'erreur
function showError(message) {
    // Crée une alerte Bootstrap
    const alertDiv = document.createElement('div');
    alertDiv.className = 'alert alert-danger alert-dismissible fade show position-fixed';
    alertDiv.style.cssText = 'top: 20px; right: 20px; z-index: 9999; min-width: 300px;';
    alertDiv.innerHTML = `
        <i class="fas fa-exclamation-triangle me-2"></i>
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    document.body.appendChild(alertDiv);
    
    // Supprime l'alerte après 5 secondes
    setTimeout(() => {
        if (alertDiv.parentNode) {
            alertDiv.parentNode.removeChild(alertDiv);
        }
    }, 5000);
}

// Affiche un message de succès
function showSuccess(message) {
    const alertDiv = document.createElement('div');
    alertDiv.className = 'alert alert-success alert-dismissible fade show position-fixed';
    alertDiv.style.cssText = 'top: 20px; right: 20px; z-index: 9999; min-width: 300px;';
    alertDiv.innerHTML = `
        <i class="fas fa-check-circle me-2"></i>
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    document.body.appendChild(alertDiv);
    
    setTimeout(() => {
        if (alertDiv.parentNode) {
            alertDiv.parentNode.removeChild(alertDiv);
        }
    }, 3000);
}
