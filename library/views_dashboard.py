from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Q
from django.utils import timezone
from django.contrib import messages
from .models import Emprunt, RetourLivre, User, Livre, Amende
from django.http import HttpResponse, JsonResponse
from .forms import LivrePhotoForm

@staff_member_required
def dashboard_return_requests(request):
    """Vue pour afficher la section des demandes de retour du dashboard."""
    # Récupérer le paramètre de recherche s'il existe
    search_query = request.GET.get('search', '')
    
    # Solution simplifiée et directe pour récupérer toutes les demandes de retour
    # Utilisation d'une requête unique et optimisée
    demandes_retour = Emprunt.objects.filter(
        est_retourne=False
    ).filter(
        Q(demande_retour=True) | Q(retours__statut='en_attente')
    )
    
    # Appliquer le filtre de recherche si un terme de recherche est fourni
    if search_query:
        demandes_retour = demandes_retour.filter(
            Q(livre__titre__icontains=search_query) | 
            Q(livre__auteur__icontains=search_query) | 
            Q(lecteur__username__icontains=search_query) |
            Q(lecteur__email__icontains=search_query)
        )
    
    # Appliquer l'ordre et la distinction
    demandes_retour = demandes_retour.distinct().order_by('-date_demande_retour', '-date_emprunt')
    
    # Logs pour débogage
    print(f"Recherche: '{search_query}'")
    print(f"Nombre total de demandes de retour trouvées: {demandes_retour.count()}")
    
    # Vérifier chaque emprunt pour s'assurer qu'il a bien une demande de retour
    for emprunt in demandes_retour:
        a_demande = emprunt.demande_retour
        a_retour_livre = emprunt.retours.filter(statut='en_attente').exists()
        print(f"Emprunt #{emprunt.id}: {emprunt.livre.titre} - {emprunt.lecteur.username}")
        print(f"  → demande_retour: {a_demande}, RetourLivre en attente: {a_retour_livre}")
    
    # Date actuelle pour les comparaisons de retard
    current_date = timezone.now().date()
    
    # Contexte pour le template
    context = {
        'demandes_retour': demandes_retour,
        'current_date': current_date,
        'search_query': search_query,
    }
    
    return render(request, 'library/dashboard_return_requests.html', context)

@staff_member_required
def debug_return_requests(request):
    """Vue de débogage pour afficher toutes les demandes de retour"""
    # Tous les emprunts
    all_emprunts = Emprunt.objects.all().order_by('-date_emprunt')
    
    # Emprunts avec demande_retour=True
    emprunts_with_demande = Emprunt.objects.filter(demande_retour=True).order_by('-date_demande_retour')
    
    # Emprunts avec RetourLivre en attente
    emprunts_with_retour = Emprunt.objects.filter(retours__statut='en_attente').distinct().order_by('-retours__date_demande')
    
    # Demandes de retour pour le tableau de bord (la même requête que pour dashboard_return_requests)
    demandes_retour = Emprunt.objects.filter(
        Q(retours__statut='en_attente') | Q(demande_retour=True)
    ).distinct().order_by('-date_demande_retour', '-retours__date_demande')
    
    context = {
        'all_emprunts': all_emprunts,
        'emprunts_with_demande': emprunts_with_demande,
        'emprunts_with_retour': emprunts_with_retour,
        'demandes_retour': demandes_retour,
    }
    
    return render(request, 'library/debug_return_requests.html', context)

@staff_member_required
def manage_book_photos(request, livre_id):
    """
    Vue pour gérer les photos d'un livre (ajout et modification)
    Permet aux administrateurs d'ajouter ou de modifier les photos d'un livre
    """
    livre = get_object_or_404(Livre, id=livre_id)
    
    if request.method == 'POST':
        form = LivrePhotoForm(request.POST, request.FILES, instance=livre)
        if form.is_valid():
            form.save()
            messages.success(request, f'Les photos du livre "{livre.titre}" ont été mises à jour avec succès.')
            return redirect('dashboard_books')
    else:
        form = LivrePhotoForm(instance=livre)
    
    context = {
        'form': form,
        'livre': livre,
    }
    
    return render(request, 'library/manage_book_photos.html', context)

@staff_member_required
def dashboard_book_photos(request):
    """
    Vue pour afficher tous les livres avec leurs photos
    Permet aux administrateurs de voir et de gérer les photos de tous les livres
    """
    livres = Livre.objects.all().order_by('titre')
    
    context = {
        'livres': livres,
    }
    
    return render(request, 'library/dashboard_book_photos.html', context)
