from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from datetime import timedelta
from .models import Livre, Emprunt, Reservation, Payment, NotationUtilisateur

@login_required
def book_details(request, livre_id):
    """Détails d'un livre."""
    livre = get_object_or_404(Livre, id=livre_id)
    
    # Récupérer la notation de l'utilisateur actuel pour ce livre (s'il en a fait une)
    user_notation = NotationUtilisateur.objects.filter(livre=livre, utilisateur=request.user).first()
    
    # Récupérer toutes les notations pour ce livre
    notations = NotationUtilisateur.objects.filter(livre=livre).order_by('-date_notation')
    
    # Obtenir la note moyenne via la méthode du modèle
    note_moyenne = livre.get_note_moyenne()
    
    # Récupérer des livres de la même catégorie
    livres_similaires = Livre.objects.filter(categorie=livre.categorie).exclude(id=livre.id)[:4]
    
    if request.method == 'POST':
        # Vérifier si l'utilisateur a des amendes non payées
        from .views import check_amende
        has_amendes, amendes_non_payees = check_amende(request)
        
        if has_amendes:
            # Forcer l'affichage du popup d'amende
            request.session['force_amende_popup'] = True
            
            # Déterminer quelle action a été tentée
            action_tentee = ''
            if 'emprunter' in request.POST:
                action_tentee = 'emprunter'
            elif 'reserver' in request.POST:
                action_tentee = 'reserver'
            elif 'reserver_payer' in request.POST:
                action_tentee = 'reserver_payer'
            
            request.session['action_tentee'] = action_tentee
            
            # Préparer le contexte avec les amendes pour afficher le popup
            paiement_effectue = Payment.objects.filter(user=request.user, livre=livre, is_valid=True).exists()
            context = {
                'livre': livre, 
                'user_notation': user_notation,
                'notations': notations,
                'note_moyenne': note_moyenne,
                'livres_similaires': livres_similaires,
                'show_amende_popup': True,
                'amendes_non_payees': amendes_non_payees,
                'action_tentee': action_tentee,
                'paiement_effectue': paiement_effectue,
                'has_amendes': has_amendes
            }
            
            # Afficher un message d'erreur
            messages.error(request, "Vous avez des amendes non payées. Veuillez les régler avant de pouvoir effectuer cette action.")
            return render(request, 'library/book_details.html', context)
        
        if 'emprunter' in request.POST:
            # Vérifier si l'utilisateur a déjà emprunté ce livre et ne l'a pas encore rendu
            emprunt_en_cours = Emprunt.objects.filter(
                livre=livre, 
                lecteur=request.user, 
                date_retour_reel__isnull=True
            ).exists()
            
            if emprunt_en_cours:
                messages.error(request, "Vous avez déjà emprunté ce livre et ne l'avez pas encore rendu.")
            elif livre.stock > 0:
                # Vérifier si l'utilisateur a une réservation non payée pour ce livre
                reservation_non_payee = Reservation.objects.filter(
                    livre=livre,
                    lecteur=request.user,
                    est_payee=False
                ).exists()
                
                if reservation_non_payee:
                    messages.error(request, "Vous avez une réservation non payée pour ce livre. Veuillez la payer avant d'emprunter.")
                    return redirect('book_details', livre_id=livre.id)
                
                livre.stock -= 1
                livre.save()
                Emprunt.objects.create(
                    livre=livre,
                    lecteur=request.user,
                    date_retour_prevue=timezone.now().date() + timedelta(days=7)
                )
                messages.success(request, "Emprunt confirmé !")
            else:
                messages.error(request, "Stock insuffisant.")
                
        elif 'reserver' in request.POST:
            # Vérifier si l'utilisateur a déjà réservé ce livre
            if Reservation.objects.filter(livre=livre, lecteur=request.user).exists():
                messages.info(request, "Vous avez déjà réservé ce livre.")
                return redirect('book_details', livre_id=livre.id)
            
            # Vérifier si l'utilisateur a déjà emprunté ce livre et ne l'a pas encore rendu
            emprunt_en_cours = Emprunt.objects.filter(
                livre=livre, 
                lecteur=request.user, 
                date_retour_reel__isnull=True
            ).exists()
            
            if emprunt_en_cours:
                messages.error(request, "Vous ne pouvez pas réserver ce livre car vous l'avez déjà emprunté.")
                return redirect('book_details', livre_id=livre.id)
            
            # Créer la réservation sans paiement
            try:
                reservation = Reservation.objects.create(
                    livre=livre,
                    lecteur=request.user,
                    est_payee=False
                )
                messages.success(request, "Réservation enregistrée sans paiement. Vous pourrez la payer plus tard.")
                return redirect('book_details', livre_id=livre.id)
            except Exception as e:
                messages.error(request, f"Erreur lors de la création de la réservation: {str(e)}")
                return redirect('book_details', livre_id=livre.id)
                
        elif 'noter' in request.POST:
            # Vérifier que la note est bien fournie
            if 'note' in request.POST:
                try:
                    note = int(request.POST.get('note', 3))
                    commentaire = request.POST.get('commentaire', '')
                    
                    # Vérifier si l'utilisateur a déjà noté ce livre
                    if user_notation:
                        # Mettre à jour la notation existante
                        user_notation.note = note
                        user_notation.commentaire = commentaire
                        user_notation.save()
                        messages.success(request, "Votre notation a été mise à jour !")
                    else:
                        # Créer une nouvelle notation
                        NotationUtilisateur.objects.create(
                            livre=livre,
                            utilisateur=request.user,
                            note=note,
                            commentaire=commentaire
                        )
                        messages.success(request, "Merci pour votre notation !")
                except (ValueError, TypeError):
                    messages.error(request, "Veuillez sélectionner une note valide.")
            else:
                messages.error(request, "Veuillez sélectionner une note.")
            
            return redirect('book_details', livre_id=livre.id)
    
    # Vérifie si le paiement a été effectué pour ce livre et cet utilisateur
    paiement_effectue = Payment.objects.filter(user=request.user, livre=livre, is_valid=True).exists()
    
    # Vérifier si l'utilisateur a des amendes non payées (pour affichage conditionnel du popup)
    from .views import check_amende
    has_amendes, amendes_non_payees = check_amende(request)
    
    context = {
        'livre': livre, 
        'paiement_effectue': paiement_effectue,
        'user_notation': user_notation,
        'notations': notations,
        'note_moyenne': note_moyenne,
        'livres_similaires': livres_similaires,
        'show_amende_popup': has_amendes and request.method == 'POST',
        'amendes_non_payees': amendes_non_payees,
        'has_amendes': has_amendes,  # Pour l'indicateur dans la barre de navigation
        'action_tentee': 'emprunter' if 'emprunter' in request.POST else ('reserver' if 'reserver' in request.POST else '')
    }
    
    return render(request, 'library/book_details.html', context)

@login_required
def book_details_json(request, livre_id):
    """API pour récupérer les détails d'un livre au format JSON"""
    from django.http import JsonResponse
    
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
        'categorie': livre.categorie,
        'description': livre.description,
        'prix': livre.prix,
        'stock': livre.stock,
        'disponible': livre.disponible,
        'photo': livre.photo.url if livre.photo else None,
        'note_moyenne': livre.get_note_moyenne(),
        'reviews': reviews_data
    }
    
    return JsonResponse(livre_data)
