from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.contrib.auth.decorators import login_required
from .models import Livre, NotationUtilisateur

@login_required
def book_details_json(request, livre_id):
    """API pour récupérer les détails d'un livre au format JSON"""
    livre = get_object_or_404(Livre, id=livre_id)
    
    # Récupérer toutes les notations pour ce livre
    notations = NotationUtilisateur.objects.filter(livre=livre).order_by('-date_notation')
    
    # Préparer les données des avis
    reviews_data = []
    for notation in notations:
        reviews_data.append({
            'id': notation.id,
            'user': notation.utilisateur.username,
            'note': notation.note,
            'commentaire': notation.commentaire,
            'date': notation.date_notation.strftime('%d/%m/%Y')
        })
    
    # Préparer les données du livre
    livre_data = {
        'id': livre.id,
        'titre': livre.titre,
        'auteur': livre.auteur,
        'categorie': getattr(livre, 'categorie', 'Non spécifiée'),
        'prix': getattr(livre, 'prix', 0),
        'stock': livre.stock,
        'disponible': livre.disponible,
        'photo': livre.photo.url if livre.photo else None,
        'note_moyenne': livre.get_note_moyenne(),
        'reviews': reviews_data
    }
    
    return JsonResponse(livre_data)
