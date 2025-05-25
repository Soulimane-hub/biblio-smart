/**
 * Fonctions simplifiées pour gérer les actions liées aux livres
 */

// Fonction pour récupérer le cookie CSRF
function getCSRFToken() {
  let cookieValue = null;
  if (document.cookie && document.cookie !== '') {
    const cookies = document.cookie.split(';');
    for (let i = 0; i < cookies.length; i++) {
      const cookie = cookies[i].trim();
      if (cookie.substring(0, 'csrftoken'.length + 1) === ('csrftoken=')) {
        cookieValue = decodeURIComponent(cookie.substring('csrftoken'.length + 1));
        break;
      }
    }
  }
  return cookieValue;
}

// Fonction pour supprimer un livre
function deleteBookAction(livreId) {
  if (confirm('Êtes-vous sûr de vouloir supprimer ce livre ? Cette action est irréversible.')) {
    // Créer un formulaire pour la suppression
    const formData = new FormData();
    formData.append('book_id', livreId);
    formData.append('formAction', 'delete');
    
    // Afficher un message de chargement
    const loadingMessage = document.createElement('div');
    loadingMessage.className = 'loading-message';
    loadingMessage.textContent = 'Suppression en cours...';
    document.body.appendChild(loadingMessage);
    
    // Envoyer la requête de suppression
    fetch('/ajouter-livre/', {
      method: 'POST',
      headers: {
        'X-CSRFToken': getCSRFToken(),
        'X-Requested-With': 'XMLHttpRequest'
      },
      body: formData
    })
    .then(response => response.json())
    .then(data => {
      // Supprimer le message de chargement
      loadingMessage.remove();
      
      if (data.success) {
        alert('Livre supprimé avec succès!');
        // Recharger la page pour voir les changements
        window.location.reload();
      } else {
        alert('Erreur: ' + (data.message || 'Une erreur est survenue lors de la suppression du livre.'));
      }
    })
    .catch(error => {
      // Supprimer le message de chargement
      loadingMessage.remove();
      
      console.error('Erreur:', error);
      alert('Une erreur est survenue lors de la suppression du livre.');
    });
  }
}

// Fonction pour voir les détails d'un livre
function viewBookDetailsAction(livreId) {
  if (confirm('Voulez-vous voir les détails de ce livre ?')) {
    // Afficher un message de chargement
    const loadingMessage = document.createElement('div');
    loadingMessage.className = 'loading-message';
    loadingMessage.textContent = 'Chargement des détails...';
    document.body.appendChild(loadingMessage);
    
    // Récupérer les détails du livre
    fetch(`/book/${livreId}/json/`, {
      method: 'GET',
      headers: {
        'X-Requested-With': 'XMLHttpRequest'
      }
    })
    .then(response => response.json())
    .then(data => {
      // Supprimer le message de chargement
      loadingMessage.remove();
      
      // Créer un modal pour afficher les détails
      const modal = document.createElement('div');
      modal.className = 'modal';
      modal.style.display = 'block';
      
      modal.innerHTML = `
        <div class="modal-content">
          <div class="modal-header">
            <h2>${data.titre}</h2>
            <span class="close">&times;</span>
          </div>
          <div class="modal-body">
            <div class="book-details">
              <div class="book-image">
                ${data.photo ? `<img src="${data.photo}" alt="${data.titre}">` : '<div class="no-image">Pas d\'image</div>'}
              </div>
              <div class="book-info">
                <p><strong>Auteur:</strong> ${data.auteur}</p>
                <p><strong>Catégorie:</strong> ${data.categorie}</p>
                <p><strong>Prix:</strong> ${data.prix} MAD</p>
                <p><strong>Stock:</strong> ${data.stock} exemplaire(s)</p>
                <p><strong>Disponible:</strong> ${data.disponible ? 'Oui' : 'Non'}</p>
              </div>
            </div>
            <div class="book-description">
              <h3>Description</h3>
              <p>${data.description || 'Aucune description disponible.'}</p>
            </div>
          </div>
        </div>
      `;
      
      // Ajouter le modal au document
      document.body.appendChild(modal);
      
      // Ajouter un gestionnaire pour fermer le modal
      const closeBtn = modal.querySelector('.close');
      closeBtn.onclick = function() {
        modal.remove();
      };
      
      // Fermer le modal si on clique en dehors
      window.onclick = function(event) {
        if (event.target == modal) {
          modal.remove();
        }
      };
    })
    .catch(error => {
      // Supprimer le message de chargement
      loadingMessage.remove();
      
      console.error('Erreur:', error);
      alert('Une erreur est survenue lors du chargement des détails du livre.');
    });
  }
}

// Fonction pour modifier un livre
function editBookAction(livreId) {
  if (confirm('Voulez-vous modifier ce livre ?')) {
    // Rediriger vers la page de modification du livre
    window.location.href = `/ajouter-livre/?book_id=${livreId}`;
  }
}

// Fonction pour ajouter un livre
function addBookAction() {
  if (confirm('Voulez-vous ajouter un nouveau livre ?')) {
    // Rediriger vers la page d'ajout de livre
    window.location.href = '/ajouter-livre/';
  }
}

// Attacher les gestionnaires d'événements lorsque le document est prêt
document.addEventListener('DOMContentLoaded', function() {
  console.log('Book actions initialized');
  
  // Bouton d'ajout de livre
  const addButton = document.querySelector('.btn-add');
  if (addButton) {
    addButton.addEventListener('click', function(event) {
      event.preventDefault();
      addBookAction();
    });
  }
  
  // Boutons d'action sur les livres
  document.querySelectorAll('.btn-crud').forEach(function(button) {
    button.addEventListener('click', function(event) {
      event.preventDefault();
      
      const livreId = this.getAttribute('data-id');
      if (!livreId) {
        console.error('Livre ID manquant');
        return;
      }
      
      if (this.classList.contains('btn-view')) {
        viewBookDetailsAction(livreId);
      } else if (this.classList.contains('btn-edit')) {
        editBookAction(livreId);
      } else if (this.classList.contains('btn-delete')) {
        deleteBookAction(livreId);
      }
    });
  });
});
