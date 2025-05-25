// Gestionnaires d'événements pour les retours de livres

document.addEventListener('DOMContentLoaded', function() {
    // Fonction pour récupérer le cookie CSRF
    function getCsrfToken() {
        return document.querySelector('input[name="csrfmiddlewaretoken"]').value;
    }

    // Fonction pour valider un retour de livre
    function validateReturn(empruntId) {
        console.log('Validation du retour pour l\'emprunt ID:', empruntId);
        if (confirm('Confirmez-vous la validation de ce retour ?')) {
            // Utiliser AJAX pour envoyer la requête
            fetch(`/validate-return/${empruntId}/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCsrfToken()
                },
                credentials: 'same-origin'
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    // Afficher un message de succès
                    alert(data.message);
                    // Recharger la page pour mettre à jour la liste des emprunts
                    window.location.reload();
                } else {
                    // Afficher un message d'erreur
                    alert('Erreur: ' + data.message);
                }
            })
            .catch(error => {
                console.error('Erreur:', error);
                alert('Une erreur est survenue lors de la validation du retour.');
            });
        }
    }

    // Fonction pour refuser un retour de livre
    function refuseReturn(empruntId) {
        console.log('Refus du retour pour l\'emprunt ID:', empruntId);
        if (confirm('Confirmez-vous le refus de cette demande de retour ?')) {
            // Utiliser AJAX pour envoyer la requête
            fetch(`/refuse-return-request/${empruntId}/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCsrfToken()
                },
                credentials: 'same-origin'
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    // Afficher un message de succès
                    alert(data.message);
                    // Recharger la page pour mettre à jour la liste des emprunts
                    window.location.reload();
                } else {
                    // Afficher un message d'erreur
                    alert('Erreur: ' + data.message);
                }
            })
            .catch(error => {
                console.error('Erreur:', error);
                alert('Une erreur est survenue lors du refus de la demande de retour.');
            });
        }
    }

    // Attacher les gestionnaires d'événements aux boutons
    document.querySelectorAll('.validate-return').forEach(button => {
        button.addEventListener('click', function(e) {
            e.preventDefault();
            const empruntId = this.getAttribute('data-emprunt-id');
            if (empruntId) {
                validateReturn(empruntId);
            }
        });
    });

    document.querySelectorAll('.refuse-return').forEach(button => {
        button.addEventListener('click', function(e) {
            e.preventDefault();
            const empruntId = this.getAttribute('data-emprunt-id');
            if (empruntId) {
                refuseReturn(empruntId);
            }
        });
    });
});
