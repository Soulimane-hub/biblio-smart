/**
 * Système de popups pour le dashboard
 * Ce fichier contient les fonctions pour afficher des popups de confirmation et de notification
 */

// Vérifier si le document est prêt
document.addEventListener('DOMContentLoaded', function() {
  console.log('Dashboard popups initialized');
  
  // Créer un conteneur pour les popups s'il n'existe pas déjà
  if (!document.getElementById('popup-container')) {
    const popupContainer = document.createElement('div');
    popupContainer.id = 'popup-container';
    document.body.appendChild(popupContainer);
  }
});

// Fonction pour créer un popup de notification
function showNotification(message, type = 'success') {
  console.log('Showing notification:', message, type);
  
  // Créer l'élément du popup
  const popup = document.createElement('div');
  popup.className = `notification-popup ${type}`;
  popup.innerHTML = `
    <div class="notification-content">
      <i class="fas ${type === 'success' ? 'fa-check-circle' : 'fa-exclamation-circle'}"></i>
      <span>${message}</span>
    </div>
    <button class="notification-close">
      <i class="fas fa-times"></i>
    </button>
  `;
  
  // Ajouter le popup au document
  document.body.appendChild(popup);
  
  // Ajouter le gestionnaire pour le bouton de fermeture
  const closeButton = popup.querySelector('.notification-close');
  closeButton.addEventListener('click', function() {
    popup.classList.remove('show');
    setTimeout(() => {
      popup.remove();
    }, 300);
  });
  
  // Faire apparaître le popup
  setTimeout(() => {
    popup.classList.add('show');
  }, 10);
  
  // Faire disparaître le popup après 5 secondes
  setTimeout(() => {
    popup.classList.remove('show');
    setTimeout(() => {
      popup.remove();
    }, 300);
  }, 5000);
}

// Fonction pour créer un popup de confirmation
function showConfirmation(message, onConfirm, onCancel = null) {
  console.log('Showing confirmation:', message);
  
  // Créer l'élément du popup
  const popup = document.createElement('div');
  popup.className = 'confirmation-popup';
  popup.innerHTML = `
    <div class="confirmation-content">
      <div class="confirmation-message">
        <i class="fas fa-question-circle"></i>
        <span>${message}</span>
      </div>
      <div class="confirmation-actions">
        <button class="btn-cancel">Annuler</button>
        <button class="btn-confirm">Confirmer</button>
      </div>
    </div>
  `;
  
  // Ajouter le popup au document
  document.body.appendChild(popup);
  
  // Fonction pour fermer le popup
  const closePopup = () => {
    popup.classList.remove('show');
    setTimeout(() => {
      popup.remove();
    }, 300);
  };
  
  // Ajouter les gestionnaires d'événements
  const cancelButton = popup.querySelector('.btn-cancel');
  const confirmButton = popup.querySelector('.btn-confirm');
  
  // Gestionnaire pour le bouton Annuler
  cancelButton.addEventListener('click', function() {
    console.log('Confirmation canceled');
    closePopup();
    if (onCancel) onCancel();
  });
  
  // Gestionnaire pour le bouton Confirmer
  confirmButton.addEventListener('click', function() {
    console.log('Confirmation confirmed');
    closePopup();
    if (onConfirm) onConfirm();
  });
  
  // Faire apparaître le popup
  setTimeout(() => {
    popup.classList.add('show');
  }, 10);
}

// Fonction pour afficher un popup de chargement
function showLoading(message = 'Chargement en cours...') {
  console.log('Showing loading:', message);
  
  // Créer l'élément du popup
  const popup = document.createElement('div');
  popup.className = 'loading-popup';
  popup.innerHTML = `
    <div class="loading-content">
      <div class="loading-spinner">
        <i class="fas fa-spinner fa-spin"></i>
      </div>
      <div class="loading-message">${message}</div>
    </div>
  `;
  
  // Ajouter le popup au document
  document.body.appendChild(popup);
  
  // Faire apparaître le popup
  setTimeout(() => {
    popup.classList.add('show');
  }, 10);
  
  // Retourner une fonction pour fermer le popup
  return function() {
    console.log('Closing loading popup');
    popup.classList.remove('show');
    setTimeout(() => {
      popup.remove();
    }, 300);
  };
}

// Remplacer les alertes par des popups de notification
window.originalAlert = window.alert;
window.alert = function(message) {
  showNotification(message, message.toLowerCase().includes('erreur') ? 'error' : 'success');
};

// Remplacer les confirmations par des popups de confirmation
window.originalConfirm = window.confirm;
window.confirm = function(message) {
  return new Promise((resolve) => {
    showConfirmation(message, () => resolve(true), () => resolve(false));
  });
};
