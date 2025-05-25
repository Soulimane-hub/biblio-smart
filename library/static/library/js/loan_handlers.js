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

// Fonction pour retourner un livre
function returnBook(empruntId) {
  console.log('Retour du livre pour l\'emprunt ID:', empruntId);
  if (confirm('Confirmez-vous le retour de ce livre ?')) {
    // Créer un formulaire pour envoyer la requête
    const form = document.createElement('form');
    form.method = 'POST';
    form.action = `/return-book/${empruntId}/`;
    
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

// Fonction pour demander un retour de livre
function requestReturn(empruntId) {
  console.log('Demande de retour pour l\'emprunt ID:', empruntId);
  if (confirm('Confirmez-vous la demande de retour pour ce livre ?')) {
    // Créer un formulaire pour envoyer la requête
    const form = document.createElement('form');
    form.method = 'POST';
    form.action = `/request-return/${empruntId}/`;
    
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

// Fonction pour valider une réservation
function validateReservation(reservationId) {
  console.log('Validation de la réservation ID:', reservationId);
  if (confirm('Confirmez-vous la validation de cette réservation ?')) {
    // Afficher le modal de validation de réservation
    const modal = document.getElementById('validateReservationModal');
    if (modal) {
      // Définir l'ID de la réservation dans le formulaire
      const form = modal.querySelector('form');
      form.querySelector('input[name="reservationId"]').value = reservationId;
      
      // Afficher le modal
      modal.style.display = 'block';
    } else {
      console.error('Modal de validation de réservation non trouvé');
      alert('Erreur: Modal de validation de réservation non trouvé');
    }
  }
}

// Fonction pour annuler une réservation
function cancelReservation(reservationId) {
  console.log('Annulation de la réservation ID:', reservationId);
  if (confirm('Confirmez-vous l\'annulation de cette réservation ?')) {
    // Créer un formulaire pour envoyer la requête
    const form = document.createElement('form');
    form.method = 'POST';
    form.action = `/reservation/${reservationId}/annuler/`;
    
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

// Fonction pour fermer les modals d'emprunt/réservation
function closeLoanModal(modalId) {
  const modal = document.getElementById(modalId);
  if (modal) modal.style.display = 'none';
}

// Fonction pour soumettre le formulaire de validation de réservation
function submitValidateReservationForm(event) {
  event.preventDefault();
  console.log('Soumission du formulaire de validation de réservation');
  
  const form = document.getElementById('validateReservationForm');
  const formData = new FormData(form);
  const reservationId = formData.get('reservationId');
  
  // Afficher un indicateur de chargement
  const submitBtn = form.querySelector('button[type="submit"]');
  const originalText = submitBtn.textContent;
  submitBtn.textContent = 'Chargement...';
  submitBtn.disabled = true;
  
  fetch(`/api/reservations/${reservationId}/validate/`, {
    method: 'POST',
    body: formData
  })
  .then(response => response.json())
  .then(data => {
    if (data.success) {
      // Fermer le modal
      closeLoanModal('validateReservationModal');
      
      // Afficher un message de succès
      alert('Réservation validée avec succès!');
      
      // Recharger la section des réservations
      loadDashboardContent('reservations');
    } else {
      alert('Erreur: ' + data.message);
    }
  })
  .catch(error => {
    console.error('Erreur:', error);
    alert('Une erreur est survenue lors de la validation de la réservation.');
  })
  .finally(() => {
    // Rétablir le bouton
    submitBtn.textContent = originalText;
    submitBtn.disabled = false;
  });
}
