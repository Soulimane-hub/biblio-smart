// Fonction pour charger le contenu des sections du dashboard
function loadDashboardContent(sectionId) {
    console.log('Chargement de la section:', sectionId);
    
    // URL des templates selon la section
    const templateUrls = {
        'users': '/dashboard/users/',
        'books': '/dashboard/books/',
        'loans': '/dashboard/loans/',
        'reservations': '/dashboard/reservations/',
        'reviews': '/dashboard/reviews/',
        'return-requests': '/dashboard/return-requests/'
    };
    
    // Vérifier si la section a une URL de template
    if (templateUrls[sectionId]) {
        // Afficher un indicateur de chargement
        document.getElementById(sectionId).innerHTML = '<div class="loading"><i class="fas fa-spinner fa-spin"></i> Chargement...</div>';
        
        // Charger le contenu via AJAX
        fetch(templateUrls[sectionId])
            .then(response => {
                if (!response.ok) {
                    throw new Error('Erreur réseau: ' + response.status);
                }
                return response.text();
            })
            .then(html => {
                // Insérer le contenu dans la section
                document.getElementById(sectionId).innerHTML = html;
                console.log('Section chargée avec succès:', sectionId);
                
                // Initialiser les gestionnaires d'événements pour les boutons
                initializeButtonHandlers(sectionId);
            })
            .catch(error => {
                console.error('Erreur lors du chargement de la section:', error);
                document.getElementById(sectionId).innerHTML = '<div class="error"><i class="fas fa-exclamation-triangle"></i> Erreur de chargement</div>';
            });
    }
}

// Fonction pour afficher une section spécifique du tableau de bord
function showSection(sectionId) {
    console.log('Affichage de la section:', sectionId);
    
    // Cacher toutes les sections
    document.querySelectorAll('.dashboard-section').forEach(function(section) {
        section.classList.remove('active');
        section.style.display = 'none';
    });
    
    // Désactiver tous les liens de la sidebar
    document.querySelectorAll('.sidebar-link').forEach(function(link) {
        link.classList.remove('active');
    });
    
    // Afficher la section demandée
    const section = document.getElementById(sectionId);
    if (section) {
        section.classList.add('active');
        section.style.display = 'block';
        
        // Charger le contenu si nécessaire
        loadDashboardContent(sectionId);
        
        console.log('Section affichée:', sectionId);
    } else {
        console.error('Section non trouvée:', sectionId);
    }
    
    // Activer le lien correspondant dans la sidebar
    const link = document.querySelector('.sidebar-link[href="#' + sectionId + '"]');
    if (link) {
        link.classList.add('active');
    }
}

// Fonction spécifique pour afficher la section des emprunts
function showLoans() {
    // Afficher la section des emprunts
    showSection('loans');
    
    // Activer le lien correspondant dans la sidebar
    document.querySelectorAll('.sidebar-link').forEach(function(link) {
        link.classList.remove('active');
    });
    
    const loansLink = document.querySelector('.sidebar-link[href="#loans"]');
    if (loansLink) {
        loansLink.classList.add('active');
    }
}

// Fonction spécifique pour afficher la section des demandes de retour
function showReturnRequests() {
    // Afficher la section des demandes de retour
    showSection('return-requests');
    
    // Activer le lien correspondant dans la sidebar
    document.querySelectorAll('.sidebar-link').forEach(function(link) {
        link.classList.remove('active');
    });
    
    const returnRequestsLink = document.querySelector('.sidebar-link[href="#return-requests"]');
    if (returnRequestsLink) {
        returnRequestsLink.classList.add('active');
    }
}

// Fonction spécifique pour afficher la section des réservations
function showReservations() {
    // Afficher la section des réservations
    showSection('reservations');
    
    // Activer le lien correspondant dans la sidebar
    document.querySelectorAll('.sidebar-link').forEach(function(link) {
        link.classList.remove('active');
    });
    
    const reservationsLink = document.querySelector('.sidebar-link[href="#reservations"]');
    if (reservationsLink) {
        reservationsLink.classList.add('active');
    }
}

// Fonction spécifique pour afficher la section des avis
function showReviews() {
    // Afficher la section des avis
    showSection('reviews');
    
    // Activer le lien correspondant dans la sidebar
    document.querySelectorAll('.sidebar-link').forEach(function(link) {
        link.classList.remove('active');
    });
    
    const reviewsLink = document.querySelector('.sidebar-link[href="#reviews"]');
    if (reviewsLink) {
        reviewsLink.classList.add('active');
    }
}

// Initialiser les gestionnaires d'événements au chargement de la page
document.addEventListener('DOMContentLoaded', function() {
    // Attacher les événements de clic aux liens de la sidebar
    document.querySelectorAll('.sidebar-link').forEach(link => {
        link.addEventListener('click', function(e) {
            if (this.getAttribute('href').startsWith('#')) {
                e.preventDefault();
                const sectionId = this.getAttribute('href').substring(1);
                showSection(sectionId);
            }
        });
    });
    
    // Vérifier si un hash existe dans l'URL et afficher la section correspondante
    if (window.location.hash) {
        const sectionId = window.location.hash.substring(1);
        if (document.getElementById(sectionId)) {
            showSection(sectionId);
        }
    } else {
        // Afficher la section statistiques par défaut
        showSection('statistics');
    }
});

// Fonction pour initialiser les gestionnaires d'événements des boutons après le chargement AJAX
function initializeButtonHandlers(sectionId) {
    console.log('Initialisation des gestionnaires d\'\u00e9vénements pour la section:', sectionId);
    
    if (sectionId === 'loans') {
        // Gestionnaires pour les boutons de validation de retour
        document.querySelectorAll('.validate-return').forEach(button => {
            button.addEventListener('click', function(e) {
                e.preventDefault();
                const empruntId = this.getAttribute('data-emprunt-id');
                if (empruntId) {
                    validateReturn(empruntId);
                }
            });
        });
        
        // Gestionnaires pour les boutons de refus de retour
        document.querySelectorAll('.refuse-return').forEach(button => {
            button.addEventListener('click', function(e) {
                e.preventDefault();
                const empruntId = this.getAttribute('data-emprunt-id');
                if (empruntId) {
                    refuseReturn(empruntId);
                }
            });
        });
        
        // Réinitialiser les gestionnaires pour les boutons de retour et de demande de retour
        document.querySelectorAll('.btn-return').forEach(button => {
            button.addEventListener('click', function() {
                const empruntId = this.getAttribute('onclick').match(/returnBook\('([^']+)'\)/)[1];
                returnBook(empruntId);
            });
            // Supprimer l'attribut onclick pour éviter les doubles appels
            button.removeAttribute('onclick');
        });
        
        document.querySelectorAll('.btn-request').forEach(button => {
            button.addEventListener('click', function() {
                const empruntId = this.getAttribute('onclick').match(/requestReturn\('([^']+)'\)/)[1];
                requestReturn(empruntId);
            });
            // Supprimer l'attribut onclick pour éviter les doubles appels
            button.removeAttribute('onclick');
        });
    } else if (sectionId === 'books') {
        console.log('Initialisation des gestionnaires pour les boutons de la section books');
        
        // Nous n'avons pas besoin d'initialiser les gestionnaires ici car ils sont déjà configurés dans le HTML
        console.log('Les boutons d\'action des livres sont déjà configurés dans le HTML');
        
        // Nous n'avons pas besoin d'initialiser le gestionnaire pour le bouton d'ajout car il est déjà configuré dans le HTML
        console.log('Le bouton d\'ajout de livre est déjà configuré dans le HTML');
    }
}
