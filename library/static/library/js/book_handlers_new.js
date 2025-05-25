/**
 * Fonctions pour gérer les actions liées aux livres
 */

// Fonction pour récupérer le cookie CSRF
function getCsrfToken() {
  return document.querySelector('input[name="csrfmiddlewaretoken"]').value;
}

// Fonction pour afficher le modal d'ajout ou de modification de livre
function showBookModal(bookId = null) {
  console.log('Affichage du modal de livre, ID:', bookId);
  
  // Afficher un popup de chargement
  const closeLoading = showLoading('Chargement du formulaire...');
  
  // URL pour récupérer le formulaire
  const url = bookId ? `/ajouter-livre/?book_id=${bookId}` : '/ajouter-livre/';
  console.log('URL du formulaire:', url);
  
  // Créer un modal pour le formulaire
  const modalId = 'bookFormModal';
  let modal = document.getElementById(modalId);
  
  // Si le modal existe déjà, le supprimer
  if (modal) {
    modal.remove();
  }
  
  // Créer un nouveau modal
  modal = document.createElement('div');
  modal.id = modalId;
  modal.className = 'modal';
  modal.innerHTML = `
    <div class="modal-content">
      <div class="modal-header">
        <h2>${bookId ? 'Modifier un livre' : 'Ajouter un livre'}</h2>
        <span class="close">&times;</span>
      </div>
      <div class="modal-body">
        <div class="loading-container">
          <i class="fas fa-spinner fa-spin"></i>
          <span>Chargement du formulaire...</span>
        </div>
      </div>
    </div>
  `;
  
  // Ajouter le modal au document
  document.body.appendChild(modal);
  
  // Afficher le modal
  modal.style.display = 'block';
  
  // Ajouter un gestionnaire pour fermer le modal
  const closeBtn = modal.querySelector('.close');
  closeBtn.onclick = function() {
    modal.style.display = 'none';
  };
  
  // Fermer le modal si on clique en dehors
  window.onclick = function(event) {
    if (event.target == modal) {
      modal.style.display = 'none';
    }
  };
  
  // Récupérer le formulaire via AJAX
  fetch(url, {
    method: 'GET',
    headers: {
      'X-Requested-With': 'XMLHttpRequest'
    }
  })
  .then(function(response) {
    if (!response.ok) {
      throw new Error('Erreur lors du chargement du formulaire');
    }
    return response.text();
  })
  .then(function(html) {
    // Fermer le popup de chargement
    closeLoading();
    console.log('Formulaire chargé avec succès');
    
    // Insérer le formulaire dans le modal
    const modalBody = modal.querySelector('.modal-body');
    modalBody.innerHTML = html;
    
    // Ajouter un gestionnaire pour le formulaire
    const form = modal.querySelector('#bookForm');
    if (form) {
      console.log('Formulaire trouvé, ajout du gestionnaire d\'événements');
      form.addEventListener('submit', function(event) {
        event.preventDefault();
        submitBookForm(form, bookId);
      });
    } else {
      console.error('Formulaire non trouvé dans la réponse HTML');
      showNotification('Erreur: Le formulaire n\'a pas pu être chargé correctement.', 'error');
    }
  })
  .catch(function(error) {
    // Fermer le popup de chargement
    closeLoading();
    
    console.error('Erreur:', error);
    showNotification('Une erreur est survenue lors du chargement du formulaire.', 'error');
  });
}

// Fonction pour voir les détails d'un livre
function viewBookDetails(livreId) {
  console.log('Affichage des détails du livre ID:', livreId);
  
  // Afficher un popup de chargement
  const closeLoading = showLoading('Chargement des détails...');
  
  // Récupérer les détails du livre via AJAX
  fetch(`/book/${livreId}/json/`, {
    method: 'GET',
    headers: {
      'X-Requested-With': 'XMLHttpRequest'
    }
  })
  .then(function(response) {
    if (!response.ok) {
      throw new Error('Erreur lors du chargement des détails du livre');
    }
    return response.json();
  })
  .then(function(data) {
    // Fermer le popup de chargement
    closeLoading();
    
    // Créer un modal pour afficher les détails
    const modalId = 'viewBookModal';
    let modal = document.getElementById(modalId);
    
    // Si le modal existe déjà, le supprimer
    if (modal) {
      modal.remove();
    }
    
    // Créer le contenu du modal
    let reviewsHtml = '';
    if (data.reviews && data.reviews.length > 0) {
      reviewsHtml = `
        <div class="book-reviews">
          <h3>Avis (${data.reviews.length})</h3>
          <div class="reviews-list">
            ${data.reviews.map(review => `
              <div class="review-item">
                <div class="review-header">
                  <div class="review-user">${review.user}</div>
                  <div class="review-date">${review.date}</div>
                </div>
                <div class="review-rating">
                  ${Array(5).fill(0).map((_, i) => 
                    i < review.note 
                      ? '<i class="fas fa-star" style="color: #ffc107;"></i>' 
                      : '<i class="far fa-star" style="color: #ffc107;"></i>'
                  ).join('')}
                </div>
                <div class="review-comment">${review.commentaire || 'Aucun commentaire'}</div>
              </div>
            `).join('')}
          </div>
        </div>
      `;
    } else {
      reviewsHtml = '<p>Aucun avis pour ce livre.</p>';
    }
    
    // Créer le modal
    modal = document.createElement('div');
    modal.id = modalId;
    modal.className = 'modal';
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
              <p><strong>Note moyenne:</strong> 
                ${data.note_moyenne > 0 
                  ? `${Array(5).fill(0).map((_, i) => 
                      i < Math.round(data.note_moyenne) 
                        ? '<i class="fas fa-star" style="color: #ffc107;"></i>' 
                        : '<i class="far fa-star" style="color: #ffc107;"></i>'
                    ).join('')} (${data.note_moyenne.toFixed(1)})` 
                  : 'Pas de note'}
              </p>
            </div>
          </div>
          <div class="book-description">
            <h3>Description</h3>
            <p>${data.description || 'Aucune description disponible.'}</p>
          </div>
          ${reviewsHtml}
        </div>
      </div>
    `;
    
    // Ajouter le modal au document
    document.body.appendChild(modal);
    
    // Afficher le modal
    modal.style.display = 'block';
    
    // Ajouter un gestionnaire pour fermer le modal
    const closeBtn = modal.querySelector('.close');
    closeBtn.onclick = function() {
      modal.style.display = 'none';
    };
    
    // Fermer le modal si on clique en dehors
    window.onclick = function(event) {
      if (event.target == modal) {
        modal.style.display = 'none';
      }
    };
  })
  .catch(function(error) {
    // Fermer le popup de chargement
    closeLoading();
    
    console.error('Erreur:', error);
    showNotification('Une erreur est survenue lors du chargement des détails du livre.', 'error');
  });
}

// Fonction pour supprimer un livre
function deleteBook(livreId) {
  console.log('Suppression du livre ID:', livreId);
  
  // Demander confirmation avant de supprimer
  showConfirmation('Êtes-vous sûr de vouloir supprimer ce livre ? Cette action est irréversible.', function() {
    console.log('Confirmation de suppression acceptée');
    
    // Afficher un popup de chargement
    const closeLoading = showLoading('Suppression en cours...');
    
    // Créer un formulaire pour la suppression
    const formData = new FormData();
    formData.append('book_id', livreId);
    formData.append('formAction', 'delete');
    
    // Envoyer la requête de suppression
    fetch('/ajouter-livre/', {
      method: 'POST',
      headers: {
        'X-CSRFToken': getCsrfToken(),
        'X-Requested-With': 'XMLHttpRequest'
      },
      body: formData
    })
    .then(function(response) {
      if (!response.ok) {
        throw new Error('Erreur lors de la suppression du livre');
      }
      return response.json();
    })
    .then(function(data) {
      // Fermer le popup de chargement
      closeLoading();
      
      if (data.success) {
        // Recharger la section des livres
        loadDashboardContent('books');
        // Afficher une notification de succès
        showNotification(data.message || 'Livre supprimé avec succès!', 'success');
      } else {
        // Afficher une notification d'erreur
        showNotification(data.message || 'Erreur lors de la suppression du livre.', 'error');
      }
    })
    .catch(function(error) {
      // Fermer le popup de chargement
      closeLoading();
      
      console.error('Erreur:', error);
      showNotification('Une erreur est survenue lors de la suppression du livre.', 'error');
    });
  });
}

// Fonction pour soumettre le formulaire d'ajout ou de modification de livre
function submitBookForm(form, bookId) {
  console.log('Soumission du formulaire de livre, ID:', bookId);
  
  // Déterminer l'action en cours
  const action = bookId ? 'Modification' : 'Ajout';
  
  // Préparer les données du formulaire
  const formData = new FormData(form);
  
  // Ajouter l'ID du livre si on est en mode modification
  if (bookId) {
    formData.append('book_id', bookId);
    formData.append('formAction', 'edit');
    console.log('Mode: Modification du livre ID', bookId);
  } else {
    formData.append('formAction', 'add');
    console.log('Mode: Ajout d\'un nouveau livre');
  }
  
  // Afficher les données du formulaire pour le débogage
  for (let pair of formData.entries()) {
    console.log(pair[0] + ': ' + pair[1]);
  }
  
  // Demander confirmation avant de soumettre le formulaire
  showConfirmation(`Confirmez-vous ${action.toLowerCase()} de ce livre ?`, function() {
    console.log('Confirmation pour soumettre le formulaire acceptée');
    
    // Afficher un popup de chargement
    const closeLoading = showLoading(`${action} du livre en cours...`);
    
    // Envoyer le formulaire via AJAX
    fetch('/ajouter-livre/', {
      method: 'POST',
      headers: {
        'X-CSRFToken': getCsrfToken(),
        'X-Requested-With': 'XMLHttpRequest'
      },
      body: formData
    })
    .then(function(response) {
      if (!response.ok) {
        throw new Error(`Erreur lors de l'${action.toLowerCase()} du livre`);
      }
      return response.json();
    })
    .then(function(data) {
      // Fermer le popup de chargement
      closeLoading();
      console.log('Réponse reçue:', data);
      
      if (data.success) {
        console.log('Opération réussie');
        
        // Fermer le modal
        const modal = document.getElementById('bookFormModal');
        if (modal) {
          modal.style.display = 'none';
          console.log('Modal fermé');
        }
        
        // Recharger la section des livres
        loadDashboardContent('books');
        console.log('Rechargement de la section des livres');
        
        // Afficher une notification de succès
        showNotification(data.message || `Livre ${bookId ? 'modifié' : 'ajouté'} avec succès!`, 'success');
      } else {
        console.error('Erreur retournée par le serveur:', data.message);
        // Afficher une notification d'erreur
        showNotification(data.message || `Une erreur est survenue lors de l'${action.toLowerCase()} du livre.`, 'error');
      }
    })
    .catch(function(error) {
      // Fermer le popup de chargement
      closeLoading();
      
      console.error('Erreur:', error);
      showNotification(`Une erreur est survenue lors de l'${action.toLowerCase()} du livre.`, 'error');
    });
  });
}

// Fonction pour ouvrir un onglet spécifique
function openBooksTab(tabName) {
  // Cacher tous les onglets
  document.querySelectorAll('.tab-content').forEach(tab => {
    tab.classList.remove('active');
  });
  
  // Désactiver tous les boutons d'onglet
  document.querySelectorAll('.tab-button').forEach(button => {
    button.classList.remove('active');
  });
  
  // Afficher l'onglet sélectionné
  document.getElementById(tabName).classList.add('active');
  
  // Activer le bouton d'onglet correspondant
  document.querySelector(`.tab-button[onclick="openBooksTab('${tabName}')"]`).classList.add('active');
}
