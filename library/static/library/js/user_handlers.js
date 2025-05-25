// Fonction pour récupérer le cookie CSRF
function getCsrfToken() {
  return document.querySelector('input[name="csrfmiddlewaretoken"]').value;
}

// Fonction pour ajouter un utilisateur
function showUserModal() {
  console.log('Ouverture du modal d\'ajout d\'utilisateur');
  // Afficher le modal d'ajout d'utilisateur
  const modal = document.getElementById('addUserModal');
  if (modal) {
    // Réinitialiser le formulaire
    const form = modal.querySelector('form');
    if (form) form.reset();
    
    // Afficher le modal
    modal.style.display = 'block';
  } else {
    console.error('Modal d\'ajout d\'utilisateur non trouvé');
    alert('Erreur: Modal d\'ajout d\'utilisateur non trouvé');
  }
}

// Fonction pour voir les détails d'un utilisateur
function viewUserDetails(userId) {
  console.log('Affichage des détails de l\'utilisateur ID:', userId);
  
  // Afficher un popup de chargement
  const closeLoading = showLoading('Chargement des détails...');
  
  // Récupérer les détails de l'utilisateur via AJAX
  fetch(`/api/users/${userId}/`, {
    method: 'GET',
    headers: {
      'X-CSRFToken': getCsrfToken(),
      'Content-Type': 'application/json'
    }
  })
  .then(response => response.json())
  .then(data => {
    // Fermer le popup de chargement
    closeLoading();
    
    if (data.success) {
      // Remplir le modal avec les détails de l'utilisateur
      const modal = document.getElementById('viewUserModal');
      if (modal) {
        // Remplir les champs du modal avec les données de l'utilisateur
        modal.querySelector('#user-username').textContent = data.user.username;
        modal.querySelector('#user-email').textContent = data.user.email;
        modal.querySelector('#user-date-joined').textContent = data.user.date_joined;
        modal.querySelector('#user-role').textContent = data.user.is_superuser ? 'Admin' : 'Lecteur';
        modal.querySelector('#user-status').textContent = data.user.is_active ? 'Actif' : 'Inactif';
        
        // Afficher le modal
        modal.style.display = 'block';
      } else {
        showNotification('Modal de détails d\'utilisateur non trouvé', 'error');
      }
    } else {
      showNotification(data.message, 'error');
    }
  })
  .catch(error => {
    // Fermer le popup de chargement
    closeLoading();
    console.error('Erreur:', error);
    showNotification('Une erreur est survenue lors de la récupération des détails de l\'utilisateur.', 'error');
  });
}

// Fonction pour éditer un utilisateur
function editUser(userId) {
  console.log('Modification de l\'utilisateur ID:', userId);
  
  // Demander confirmation avant de modifier
  showConfirmation('Voulez-vous modifier cet utilisateur ?', () => {
    // Afficher un popup de chargement
    const closeLoading = showLoading('Chargement des données...');
    
    // Récupérer les détails de l'utilisateur via AJAX
    fetch(`/api/users/${userId}/`, {
      method: 'GET',
      headers: {
        'X-CSRFToken': getCsrfToken(),
        'Content-Type': 'application/json'
      }
    })
    .then(response => response.json())
    .then(data => {
      // Fermer le popup de chargement
      closeLoading();
      
      if (data.success) {
        // Remplir le modal avec les détails de l'utilisateur
        const modal = document.getElementById('editUserModal');
        if (modal) {
          // Remplir les champs du formulaire avec les données de l'utilisateur
          const form = modal.querySelector('form');
          form.querySelector('input[name="userId"]').value = userId;
          form.querySelector('input[name="username"]').value = data.user.username;
          form.querySelector('input[name="email"]').value = data.user.email;
          form.querySelector('select[name="role"]').value = data.user.is_superuser ? 'admin' : 'reader';
          form.querySelector('select[name="status"]').value = data.user.is_active ? 'active' : 'inactive';
          
          // Afficher le modal
          modal.style.display = 'block';
        } else {
          showNotification('Modal d\'édition d\'utilisateur non trouvé', 'error');
        }
      } else {
        showNotification(data.message, 'error');
      }
    })
    .catch(error => {
      // Fermer le popup de chargement
      closeLoading();
      console.error('Erreur:', error);
      showNotification('Une erreur est survenue lors de la récupération des détails de l\'utilisateur.', 'error');
    });
  });
}

// Fonction pour supprimer un utilisateur
function deleteUser(userId) {
  console.log('Suppression de l\'utilisateur ID:', userId);
  
  // Utiliser notre popup de confirmation
  showConfirmation('Êtes-vous sûr de vouloir supprimer cet utilisateur ?', () => {
    // Afficher un popup de chargement
    const closeLoading = showLoading('Suppression en cours...');
    
    // Envoyer une requête AJAX pour supprimer l'utilisateur
    fetch(`/api/users/${userId}/delete/`, {
      method: 'POST',
      headers: {
        'X-CSRFToken': getCsrfToken(),
        'Content-Type': 'application/json'
      }
    })
    .then(response => response.json())
    .then(data => {
      // Fermer le popup de chargement
      closeLoading();
      
      if (data.success) {
        // Recharger la section des utilisateurs
        loadDashboardContent('users');
        // Afficher une notification de succès
        showNotification(data.message || 'Utilisateur supprimé avec succès!', 'success');
      } else {
        // Afficher une notification d'erreur
        showNotification(data.message, 'error');
      }
    })
    .catch(error => {
      // Fermer le popup de chargement
      closeLoading();
      
      console.error('Erreur:', error);
      showNotification('Une erreur est survenue lors de la suppression de l\'utilisateur.', 'error');
    });
  });
}

// Fonction pour fermer les modals d'utilisateur
function closeUserModal(modalId) {
  const modal = document.getElementById(modalId);
  if (modal) modal.style.display = 'none';
}

// Fonction pour soumettre le formulaire d'ajout d'utilisateur
function submitAddUserForm(event) {
  event.preventDefault();
  console.log('Soumission du formulaire d\'ajout d\'utilisateur');
  
  // Afficher un popup de chargement
  const closeLoading = showLoading('Ajout de l\'utilisateur en cours...');
  
  const form = document.getElementById('addUserForm');
  const formData = new FormData(form);
  
  fetch('/api/users/add/', {
    method: 'POST',
    body: formData
  })
  .then(response => response.json())
  .then(data => {
    // Fermer le popup de chargement
    closeLoading();
    
    if (data.success) {
      // Fermer le modal
      closeUserModal('addUserModal');
      
      // Afficher une notification de succès
      showNotification(data.message || 'Utilisateur ajouté avec succès!', 'success');
      
      // Recharger la section des utilisateurs
      loadDashboardContent('users');
    } else {
      // Afficher une notification d'erreur
      showNotification(data.message, 'error');
    }
  })
  .catch(error => {
    // Fermer le popup de chargement
    closeLoading();
    
    console.error('Erreur:', error);
    showNotification('Une erreur est survenue lors de l\'ajout de l\'utilisateur.', 'error');
  });
}

// Fonction pour soumettre le formulaire d'édition d'utilisateur
function submitEditUserForm(event) {
  event.preventDefault();
  console.log('Soumission du formulaire d\'\u00e9dition d\'utilisateur');
  
  // Afficher un popup de chargement
  const closeLoading = showLoading('Modification de l\'utilisateur en cours...');
  
  const form = document.getElementById('editUserForm');
  const formData = new FormData(form);
  const userId = formData.get('userId');
  
  fetch(`/api/users/${userId}/edit/`, {
    method: 'POST',
    body: formData
  })
  .then(response => response.json())
  .then(data => {
    // Fermer le popup de chargement
    closeLoading();
    
    if (data.success) {
      // Fermer le modal
      closeUserModal('editUserModal');
      
      // Afficher une notification de succès
      showNotification(data.message || 'Utilisateur modifié avec succès!', 'success');
      
      // Recharger la section des utilisateurs
      loadDashboardContent('users');
    } else {
      // Afficher une notification d'erreur
      showNotification(data.message, 'error');
    }
  })
  .catch(error => {
    // Fermer le popup de chargement
    closeLoading();
    
    console.error('Erreur:', error);
    showNotification('Une erreur est survenue lors de la modification de l\'utilisateur.', 'error');
  });
}
