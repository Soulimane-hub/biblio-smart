// Fonction pour récupérer le cookie CSRF
function getCsrfToken() {
  return document.querySelector('input[name="csrfmiddlewaretoken"]').value;
}

// Fonction pour supprimer un avis
function deleteReview(reviewId) {
  console.log('Suppression de l\'avis ID:', reviewId);
  if (confirm('Êtes-vous sûr de vouloir supprimer cet avis ?')) {
    // Créer un formulaire pour envoyer la requête
    const form = document.createElement('form');
    form.method = 'POST';
    form.action = `/delete-review/${reviewId}/`;
    
    // Ajouter le token CSRF
    const csrfInput = document.createElement('input');
    csrfInput.type = 'hidden';
    csrfInput.name = 'csrfmiddlewaretoken';
    csrfInput.value = getCsrfToken();
    form.appendChild(csrfInput);
    
    // Ajouter au document et soumettre
    document.body.appendChild(form);
    form.submit();
  }
}

// Fonction pour voir les détails d'un avis
function viewReviewDetails(reviewId) {
  console.log('Affichage des détails de l\'avis ID:', reviewId);
  
  // Récupérer les détails de l'avis via AJAX
  fetch(`/api/reviews/${reviewId}/`, {
    method: 'GET',
    headers: {
      'X-CSRFToken': getCsrfToken(),
      'Content-Type': 'application/json'
    }
  })
  .then(response => response.json())
  .then(data => {
    if (data.success) {
      // Remplir le modal avec les détails de l'avis
      const modal = document.getElementById('viewReviewModal');
      if (modal) {
        // Remplir les champs du modal avec les données de l'avis
        modal.querySelector('#review-livre').textContent = data.review.livre_titre;
        modal.querySelector('#review-user').textContent = data.review.user_username;
        modal.querySelector('#review-date').textContent = data.review.date_creation;
        modal.querySelector('#review-note').textContent = data.review.note + ' / 5';
        modal.querySelector('#review-commentaire').textContent = data.review.commentaire;
        
        // Afficher le modal
        modal.style.display = 'block';
      } else {
        console.error('Modal de détails d\'avis non trouvé');
        alert('Erreur: Modal de détails d\'avis non trouvé');
      }
    } else {
      alert('Erreur: ' + data.message);
    }
  })
  .catch(error => {
    console.error('Erreur:', error);
    alert('Une erreur est survenue lors de la récupération des détails de l\'avis.');
  });
}

// Fonction pour fermer les modals d'avis
function closeReviewModal(modalId) {
  const modal = document.getElementById(modalId);
  if (modal) modal.style.display = 'none';
}
