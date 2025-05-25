/**
 * Fonctions pour gérer les actions des livres avec des popups
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
  let url;
  if (bookId) {
    // Pour la modification, utiliser une URL directe vers le formulaire d'édition
    url = `/modifier-livre/${bookId}/`;
  } else {
    // Pour l'ajout, utiliser l'URL existante
    url = '/ajouter-livre/?ajax=form';
  }
  console.log('URL du formulaire:', url);
  
  // Récupérer le formulaire via AJAX
  fetch(url, {
    method: 'GET',
    headers: {
      'X-Requested-With': 'XMLHttpRequest',
      'Accept': 'text/html'
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
          ${html}
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
    
    // Modifier le formulaire pour qu'il se soumette directement au serveur sans AJAX
    const form = modal.querySelector('form');
    if (form) {
      // Modifier l'action du formulaire pour qu'il pointe vers la bonne URL
      if (bookId) {
        form.action = `/modifier-livre/${bookId}/`;
        form.method = 'POST';
      } else {
        form.action = '/ajouter-livre/';
        form.method = 'POST';
      }
      
      // Ajouter un champ caché pour indiquer que c'est une soumission AJAX
      const ajaxInput = document.createElement('input');
      ajaxInput.type = 'hidden';
      ajaxInput.name = 'is_ajax';
      ajaxInput.value = 'true';
      form.appendChild(ajaxInput);
      
      // Remplacer la soumission normale par notre fonction personnalisée
      form.addEventListener('submit', function(event) {
        event.preventDefault();
        
        // Afficher une confirmation
        const action = bookId ? 'modification' : 'ajout';
        showConfirmation(`Confirmez-vous la ${action} de ce livre ?`, function() {
          // Créer un FormData à partir du formulaire
          const formData = new FormData(form);
          
          // Vérifier si un fichier a été sélectionné
          const photoInput = form.querySelector('input[name="photo"]');
          if (photoInput && photoInput.files && photoInput.files.length > 0) {
            console.log('Photo sélectionnée:', photoInput.files[0].name, 'taille:', photoInput.files[0].size);
          } else {
            console.log('Aucune nouvelle photo sélectionnée');
          }
          
          // Ajouter l'ID du livre si c'est une modification
          if (bookId) {
            formData.append('bookId', bookId);
          }
          
          // Afficher un popup de chargement
          const closeLoading = showLoading(`${bookId ? 'Modification' : 'Ajout'} du livre en cours...`);
          
          // Envoyer le formulaire via AJAX
          fetch(form.action, {
            method: 'POST',
            body: formData,
            // Ne pas définir de Content-Type, le navigateur le fera automatiquement avec la boundary pour multipart/form-data
            headers: {
              'X-Requested-With': 'XMLHttpRequest'
            }
          })
          .then(response => response.json())
          .then(data => {
            // Fermer le popup de chargement
            closeLoading();
            
            if (data.success) {
              // Fermer le modal
              modal.style.display = 'none';
              
              // Afficher une notification de succès
              showNotification(data.message || `Livre ${bookId ? 'modifié' : 'ajouté'} avec succès!`, 'success');
              
              // Recharger la section des livres
              loadDashboardContent('books');
            } else {
              // Afficher une notification d'erreur
              showNotification(data.message || `Erreur lors de l'${action} du livre.`, 'error');
            }
          })
          .catch(error => {
            // Fermer le popup de chargement
            closeLoading();
            
            // Afficher une notification d'erreur
            console.error('Erreur:', error);
            showNotification(`Une erreur est survenue lors de l'${action} du livre.`, 'error');
          });
        });
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
              <p><strong>Auteur:</strong> ${data.auteur || 'Non spécifié'}</p>
              <p><strong>Catégorie:</strong> ${data.categorie || 'Non spécifiée'}</p>
              <p><strong>Prix:</strong> ${data.prix ? data.prix + ' MAD' : 'Non spécifié'}</p>
              <p><strong>Stock:</strong> ${data.stock} exemplaire(s)</p>
              <p><strong>Disponible:</strong> ${data.disponible ? 'Oui' : 'Non'}</p>
              <p><strong>Note moyenne:</strong> 
                ${data.note_moyenne > 0 
                  ? `${Array(5).fill(0).map((_, i) => 
                      i < Math.round(data.note_moyenne) 
                        ? '<i class="fas fa-star" style="color: #ffc107;"></i>' 
                        : '<i class="far fa-star" style="color: #ffc107;"></i>'
                    ).join('')} (${parseFloat(data.note_moyenne).toFixed(1)})` 
                  : 'Pas de note'}
              </p>
            </div>
          </div>
          <!-- La section de description a été supprimée -->
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
    formData.append('bookId', livreId);
    formData.append('formAction', 'delete');
    
    console.log('Données envoyées pour la suppression:', livreId);
    
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
  
  // Créer un nouvel objet FormData pour le formulaire
  const formData = new FormData();
  
  // Ajouter le jeton CSRF
  const csrfToken = document.querySelector('input[name="csrfmiddlewaretoken"]').value;
  formData.append('csrfmiddlewaretoken', csrfToken);
  
  // Ajouter tous les champs du formulaire original sauf bookId et formAction
  const originalFormData = new FormData(form);
  for (let pair of originalFormData.entries()) {
    if (pair[0] !== 'bookId' && pair[0] !== 'formAction') {
      formData.append(pair[0], pair[1]);
      console.log('Ajout de ' + pair[0] + ': ' + pair[1]);
    }
  }
  
  // Déterminer l'action en cours et ajouter les paramètres appropriés
  if (bookId) {
    // Mode modification
    formData.append('bookId', bookId);
    formData.append('formAction', 'edit');
    console.log('Mode: Modification du livre ID ' + bookId);
  } else {
    // Mode ajout
    formData.append('formAction', 'add');
    console.log('Mode: Ajout d\'un nouveau livre');
  }
  
  // Afficher toutes les données du formulaire pour le débogage
  console.log('Données finales du formulaire:');
  for (let pair of formData.entries()) {
    console.log(pair[0] + ': ' + pair[1]);
  }
  
  // Déterminer l'action en cours pour les messages
  const actionLabel = bookId ? 'Modification' : 'Ajout';
  
  // Demander confirmation avant de soumettre le formulaire
  showConfirmation(`Confirmez-vous la ${actionLabel.toLowerCase()} de ce livre ?`, function() {
    // Afficher un popup de chargement
    const closeLoading = showLoading(`${actionLabel} du livre en cours...`);
    
    // Envoyer le formulaire via AJAX
    fetch('/ajouter-livre/', {
      method: 'POST',
      headers: {
        'X-Requested-With': 'XMLHttpRequest'
      },
      body: formData
    })
    .then(function(response) {
      if (!response.ok) {
        throw new Error(`Erreur lors de la ${actionLabel.toLowerCase()} du livre`);
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
        showNotification(data.message || `Une erreur est survenue lors de la ${actionLabel.toLowerCase()} du livre.`, 'error');
      }
    })
    .catch(function(error) {
      // Fermer le popup de chargement
      closeLoading();
      
      console.error('Erreur:', error);
      showNotification(`Une erreur est survenue lors de la ${actionLabel.toLowerCase()} du livre.`, 'error');
    });
  });
}

// Fonction pour ouvrir un onglet spécifique dans la section des livres
function openBooksTab(tabName) {
  console.log('Ouverture de l\'onglet:', tabName);
  
  // Cacher tous les contenus d'onglets
  const tabContents = document.querySelectorAll('.tab-content');
  tabContents.forEach(content => {
    content.classList.remove('active');
  });
  
  // Désactiver tous les boutons d'onglets
  const tabButtons = document.querySelectorAll('.tab-button');
  tabButtons.forEach(button => {
    button.classList.remove('active');
  });
  
  // Afficher le contenu de l'onglet sélectionné
  const selectedTab = document.getElementById(tabName);
  if (selectedTab) {
    selectedTab.classList.add('active');
  } else {
    console.error('Onglet non trouvé:', tabName);
  }
  
  // Activer le bouton d'onglet correspondant
  const selectedButton = document.querySelector(`.tab-button[onclick="openBooksTab('${tabName}')"]`);
  if (selectedButton) {
    selectedButton.classList.add('active');
  } else {
    console.error('Bouton d\'onglet non trouvé pour:', tabName);
  }
}
