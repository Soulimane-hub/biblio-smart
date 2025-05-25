/**
 * Fonctions simples pour gérer les actions des livres
 */

// Fonction pour afficher un livre
function viewBookDetails(livreId) {
  // Rediriger vers la page de détails du livre
  window.location.href = '/book/' + livreId + '/';
}

// Fonction pour modifier un livre
function showBookModal(livreId) {
  // Rediriger vers la page d'ajout/modification de livre avec l'ID du livre
  window.location.href = '/ajouter-livre/?book_id=' + livreId;
}

// Fonction pour supprimer un livre
function deleteBook(livreId) {
  // Demander confirmation
  if (confirm('Êtes-vous sûr de vouloir supprimer ce livre ?')) {
    // Créer un formulaire pour soumettre la demande de suppression
    const form = document.createElement('form');
    form.method = 'POST';
    form.action = '/ajouter-livre/';
    
    // Ajouter le token CSRF
    const csrfInput = document.createElement('input');
    csrfInput.type = 'hidden';
    csrfInput.name = 'csrfmiddlewaretoken';
    csrfInput.value = document.querySelector('input[name="csrfmiddlewaretoken"]').value;
    form.appendChild(csrfInput);
    
    // Ajouter l'ID du livre
    const bookIdInput = document.createElement('input');
    bookIdInput.type = 'hidden';
    bookIdInput.name = 'book_id';
    bookIdInput.value = livreId;
    form.appendChild(bookIdInput);
    
    // Ajouter l'action
    const actionInput = document.createElement('input');
    actionInput.type = 'hidden';
    actionInput.name = 'formAction';
    actionInput.value = 'delete';
    form.appendChild(actionInput);
    
    // Ajouter le formulaire au document et le soumettre
    document.body.appendChild(form);
    form.submit();
  }
}
