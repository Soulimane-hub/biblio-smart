from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse
from django.contrib import messages
from reportlab.lib import colors
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.core.mail import send_mail
from django.urls import reverse
from django.conf import settings
from django.contrib.auth import login, authenticate
from django.contrib.auth.models import User
from django.db.models import Count, Avg, Sum, Q, F, ExpressionWrapper, fields, Case, When, Value
from django.db.models.functions import ExtractMonth, ExtractYear, Coalesce
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from .models import (
    Livre, Emprunt, Reservation, Amende, Payment, 
    NotationUtilisateur, RetourLivre
)
from datetime import timedelta, datetime
from django.utils import timezone
from django import forms
from django.http import HttpResponseForbidden, HttpResponse
from django.shortcuts import get_object_or_404
import io
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
import json
import calendar

# def notifier_disponibilite_livre(reservation):
#     lecteur = reservation.lecteur
#     livre = reservation.livre
#     # Remplacez ceci par l'URL de votre site si settings.SITE_URL n'existe pas
#     site_url = getattr(settings, 'SITE_URL', 'http://localhost:8000')
#     payer_url = f"{site_url}{reverse('payer_reservation', args=[reservation.id])}"
#     annuler_url = f"{site_url}{reverse('annuler_reservation', args=[reservation.id])}"
#     sujet = f"Votre livre '{livre.titre}' est disponible !"
#     message = (
#         f"Bonjour {lecteur.username},\n\n"
#         f"Le livre '{livre.titre}' que vous avez rÃ©servÃ© est maintenant disponible.\n"
#         f"Vous pouvez :\n"
#         f"- Payer la rÃ©servation pour l'emprunter : {payer_url}\n"
#         f"- Annuler la rÃ©servation : {annuler_url}\n\n"
#         f"Cordialement,\nL'Ã©quipe de la bibliothÃ¨que"
#     )
#     send_mail(
#         sujet,
#         message,
#         settings.DEFAULT_FROM_EMAIL,
#         [lecteur.email],
#         fail_silently=False,
#     )

def check_amende(request):
    """VÃ©rifie si l'utilisateur a des amendes non payÃ©es et les rÃ©cupÃ¨re."""
    amendes_non_payees = Amende.objects.filter(lecteur=request.user, payee=False).order_by('-id')
    if amendes_non_payees.exists():
        request.session['show_amende_popup'] = True
        return True, amendes_non_payees
    return False, None

@login_required
def reserver_livre(request, livre_id):
    from .models import Amende, Livre, Emprunt, Reservation
    livre = get_object_or_404(Livre, id=livre_id)
    
    # VÃ©rifier si l'utilisateur a des amendes non payÃ©es
    has_amendes, amendes_non_payees = check_amende(request)
    if has_amendes:
        # Forcer l'affichage du popup d'amende
        request.session['force_amende_popup'] = True
        request.session['action_tentee'] = 'reserver'
        
        # Rediriger vers la page de dÃ©tails du livre avec un message d'erreur
        messages.error(request, "Vous avez des amendes non payÃ©es. Veuillez les rÃ©gler avant de pouvoir rÃ©server un livre.")
        return redirect('book_details', livre_id=livre.id)
    
    # VÃ©rifier si le livre est disponible pour rÃ©servation
    if livre.stock <= 0:
        messages.error(request, "Ce livre n'est plus disponible pour rÃ©servation immÃ©diate.")
        return redirect('book_details', livre_id=livre.id)
    
    # VÃ©rifier si l'utilisateur a dÃ©jÃ  rÃ©servÃ© ce livre
    if Reservation.objects.filter(livre=livre, lecteur=request.user).exists():
        messages.info(request, "Vous avez dÃ©jÃ  rÃ©servÃ© ce livre.")
        return redirect('book_details', livre_id=livre.id)
    
    # VÃ©rifier si l'utilisateur a dÃ©jÃ  empruntÃ© ce livre et ne l'a pas encore rendu
    emprunt_en_cours = Emprunt.objects.filter(
        livre=livre, 
        lecteur=request.user, 
        est_retourne=False
    ).exists()
    
    if emprunt_en_cours:
        messages.error(request, "Vous ne pouvez pas rÃ©server ce livre car vous l'avez dÃ©jÃ  empruntÃ©.")
        return redirect('book_details', livre_id=livre.id)
    
    # CrÃ©er la rÃ©servation
    Reservation.objects.create(livre=livre, lecteur=request.user)
    messages.success(request, "RÃ©servation effectuÃ©e avec succÃ¨s. ProcÃ©dez au paiement pour finaliser l'emprunt.")
    return redirect('book_details', livre_id=livre.id)

@login_required
def payer_livre(request, livre_id):
    from .models import Amende, Livre, Reservation, Emprunt, Payment
    livre = get_object_or_404(Livre, id=livre_id)
    
    # VÃ©rifier si l'utilisateur a des amendes non payÃ©es
    has_amendes, amendes_non_payees = check_amende(request)
    if has_amendes:
        # Forcer l'affichage du popup d'amende
        request.session['force_amende_popup'] = True
        request.session['action_tentee'] = 'emprunter'
        
        # Rediriger vers la page de dÃ©tails du livre avec un message d'erreur
        messages.error(request, "Vous avez des amendes non payÃ©es. Veuillez les rÃ©gler avant de pouvoir emprunter un livre.")
        return redirect('book_details', livre_id=livre.id)
    
    # VÃ©rifier si une rÃ©servation existe dÃ©jÃ  pour ce livre et cet utilisateur
    existing_reservation = Reservation.objects.filter(livre=livre, lecteur=request.user).first()
    
    if request.method == 'POST':
        # CrÃ©er l'emprunt
        date_emprunt = timezone.now().date()
        date_retour_prevue = date_emprunt + timedelta(days=7)
        emprunt = Emprunt.objects.create(
            livre=livre,
            lecteur=request.user,
            date_emprunt=date_emprunt,
            date_retour_prevue=date_retour_prevue
        )
        
        # CrÃ©er le paiement
        payment = Payment.objects.create(
            user=request.user, 
            livre=livre, 
            emprunt=emprunt, 
            amount=livre.prix, 
            is_valid=True,
            description=f"Paiement pour emprunt du livre '{livre.titre}'"
        )
        
        # Mettre Ã  jour le stock
        livre.stock -= 1
        livre.save()
        
        # Si une rÃ©servation existait, la supprimer car l'emprunt est maintenant effectuÃ©
        if existing_reservation:
            existing_reservation.delete()
        
        messages.success(request, "Emprunt effectuÃ© avec succÃ¨s !")
        return redirect('book_details', livre_id=livre.id)
    
    return render(request, 'library/payer_emprunt.html', {'livre': livre})

from django.urls import reverse
from django.contrib.auth.decorators import login_required

from django.contrib import messages

 


class CustomUserCreationForm(forms.ModelForm):
    email = forms.EmailField(required=True, help_text='Requis. Entrez une adresse email valide.')
    username = forms.CharField(max_length=150, required=True, help_text='Requis. Nom d\'utilisateur.')
    password1 = forms.CharField(label='Mot de passe', widget=forms.PasswordInput, required=True)

    class Meta:
        model = User
        fields = ("username", "email", "password1")

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("Cet email est dÃ©jÃ  utilisÃ©.")
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"]
        user.set_password(self.cleaned_data["password1"])
        user.is_superuser = False
        user.is_staff = False
        # Couleurs - ThÃ¨me bibliothÃ¨que
        couleur_primaire = colors.HexColor('#5e4b3e')  # Brun foncÃ© (comme la navbar)
        couleur_secondaire = colors.HexColor('#f5f1e8')  # Beige clair (comme le fond)
        couleur_texte = colors.HexColor('#2c2416')  # Brun trÃ¨s foncÃ© (pour le texte)
        couleur_accent = colors.HexColor('#c9b18c')  # DorÃ© (pour les accents)
        couleur_highlight = colors.HexColor('#8a7866')  # Brun moyen (pour les titres)
        if commit:
            user.save()
        return user

def register(request):
    form = CustomUserCreationForm()
    # Supprimer les messages si GET (rafraÃ®chissement ou accÃ¨s direct)
    if request.method == 'GET':
        storage = messages.get_messages(request)
        list(storage)  # Vide le storage
    if request.method == 'POST':
        # SIGN UP
        if 'username' in request.POST and 'email' in request.POST and 'password1' in request.POST:
            form = CustomUserCreationForm({
                'username': request.POST.get('username'),
                'email': request.POST.get('email'),
                'password1': request.POST.get('password1'),
            })
            if form.is_valid():
                user = form.save()
                user_auth = authenticate(username=user.username, password=request.POST.get('password1'))
                if user_auth is not None:
                    login(request, user_auth)
                    return redirect('register')
                else:
                    messages.success(request, "Inscription rÃ©ussie, mais connexion automatique impossible. Veuillez vous connecter.")
                    return redirect('register')
            else:
                for field, errors in form.errors.items():
                    for error in errors:
                        messages.error(request, f"{form.fields[field].label if field in form.fields else field} : {error}")
        # SIGN IN
        elif 'email' in request.POST and 'password' in request.POST:
            email = request.POST.get('email')
            password = request.POST.get('password')
            try:
                user = User.objects.get(email=email)
                user_auth = authenticate(username=user.username, password=password)
                if user_auth is not None:
                    login(request, user_auth)
                    if user_auth.is_superuser:
                        return redirect('dashboard')
                    else:
                        return redirect('home')
                else:
                    messages.error(request, "Mot de passe incorrect.")
            except User.DoesNotExist:
                messages.error(request, "Utilisateur non trouvÃ©.")
    return render(request, 'library/register.html', {
        'form': form,
        'form_type': 'register'
    })

def csrf_failure(request, reason=""):
    """Page d'erreur CSRF personnalisÃ©e."""
    return HttpResponseForbidden("CSRF verification failed.")

# La fonction payments a Ã©tÃ© supprimÃ©e car nous redirigeons directement vers le tÃ©lÃ©chargement du reÃ§u

@login_required
def payer_amende(request, amende_id):
    """Permet Ã  un utilisateur de payer une amende."""
    from .models import Amende, Payment
    from django.utils import timezone
    
    # RÃ©cupÃ©rer l'amende
    amende = get_object_or_404(Amende, id=amende_id, lecteur=request.user, payee=False)
    
    if request.method == 'POST':
        # VÃ©rifier que tous les champs du formulaire sont remplis
        cardholder = request.POST.get('cardholder')
        cardnumber = request.POST.get('cardnumber')
        expdate = request.POST.get('expdate')
        cvv = request.POST.get('cvv')
        
        if not all([cardholder, cardnumber, expdate, cvv]):
            messages.error(request, "Veuillez remplir tous les champs du formulaire de paiement.")
            return render(request, 'library/payer_amende.html', {'amende': amende})
        
        # VÃ©rification de base du format des donnÃ©es de carte
        import re
        if not re.match(r'^[0-9 ]{13,19}$', cardnumber):
            messages.error(request, "Le numÃ©ro de carte n'est pas valide.")
            return render(request, 'library/payer_amende.html', {'amende': amende})
        
        if not re.match(r'^(0[1-9]|1[0-2])\/\d{2}$', expdate):
            messages.error(request, "La date d'expiration n'est pas valide. Utilisez le format MM/AA.")
            return render(request, 'library/payer_amende.html', {'amende': amende})
        
        if not re.match(r'^\d{3,4}$', cvv):
            messages.error(request, "Le code CVV n'est pas valide.")
            return render(request, 'library/payer_amende.html', {'amende': amende})
        
        # Paiement acceptÃ©
        # CrÃ©er le paiement
        payment = Payment.objects.create(
            user=request.user,
            livre=amende.emprunt.livre,  
            amount=amende.montant,
            is_valid=True,
            description=f"Paiement d'amende pour {amende.raison}"
        )
        
        # Marquer l'amende comme payÃ©e
        amende.payee = True
        amende.montant_paye = amende.montant
        amende.save()
        
        messages.success(request, "Amende payÃ©e avec succÃ¨s !")
        
        # Rediriger vers la page de dÃ©tails du livre
        livre_id = amende.emprunt.livre.id
        return redirect('book_details', livre_id=livre_id)
    
    return render(request, 'library/payer_amende.html', {'amende': amende})

@login_required
def notifications(request):
    """Affiche uniquement les notifications concernant la disponibilitÃ© des livres rÃ©servÃ©s."""
    from .models import Reservation, Livre
    
    # RÃ©cupÃ©rer uniquement les rÃ©servations notifiÃ©es (livre disponible, en attente de paiement)
    reservations_notifiees = Reservation.objects.filter(
        lecteur=request.user,
        notification_envoyee=True,
        est_payee=False
    ).order_by('-date_notification')
    
    # Traiter les actions (payer ou annuler)
    if request.method == 'POST':
        action = request.POST.get('action')
        reservation_id = request.POST.get('reservation_id')
        
        if reservation_id:
            reservation = get_object_or_404(Reservation, id=reservation_id, lecteur=request.user)
            
            if action == 'payer':
                # Rediriger vers la page de paiement d'emprunt
                return redirect('payer_emprunt', reservation_id=reservation.id)
            
            elif action == 'annuler':
                # Annuler la rÃ©servation
                livre = reservation.livre
                reservation.delete()
                messages.success(request, f"Votre rÃ©servation pour '{livre.titre}' a Ã©tÃ© annulÃ©e.")
                return redirect('notifications')
    
    return render(request, 'library/notifications.html', {
        'reservations_notifiees': reservations_notifiees,
        # Envoyer des listes vides pour les autres catÃ©gories
        'reservations_payees': [],
        'reservations_en_attente': []
    })

@login_required
def home(request):
    """Page d'accueil avec filtrage par catÃ©gorie et recherche."""
    from .models import Livre, Reservation
    # Filtrage par catÃ©gorie
    categorie = request.GET.get('categorie', '')
    recherche = request.GET.get('q', '')
    
    # Filtrage par recherche
    livres = Livre.objects.all()
    if categorie and categorie != 'toutes':
        livres = livres.filter(categorie=categorie)
    if recherche:
        # Recherche dans le titre, l'auteur ou l'ISBN
        livres = livres.filter(
            Q(titre__icontains=recherche) | 
            Q(auteur__icontains=recherche) | 
            Q(isbn__icontains=recherche)
        )
    
    # Obtenir toutes les catÃ©gories pour le menu dÃ©roulant
    categories = [choice[0] for choice in Livre.CATEGORIES_CHOICES]
    
    # VÃ©rifier les amendes non payÃ©es mais ne pas afficher le popup automatiquement
    has_amendes, amendes_non_payees = check_amende(request)
    
    # Compter les notifications (rÃ©servations non payÃ©es et notifiÃ©es)
    notifications_count = Reservation.objects.filter(
        lecteur=request.user,
        est_payee=False,
        notification_envoyee=True
    ).count()
    
    return render(request, 'library/home.html', {
        'livres': livres,
        'categories': categories,
        'categorie_selectionnee': categorie,
        'recherche': recherche,
        'show_amende_popup': False,  # Ne pas afficher le popup automatiquement
        'amendes_non_payees': amendes_non_payees,
        'has_amendes': has_amendes,  # Pour l'indicateur dans la barre de navigation
        'notifications_count': notifications_count
    })

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
def history(request):
    """Historique des emprunts et rÃ©servations de l'utilisateur."""
    today = timezone.now().date()
    emprunts = Emprunt.objects.filter(lecteur=request.user).order_by('-date_emprunt')
    reservations = Reservation.objects.filter(lecteur=request.user).order_by('-date_reservation')
    amendes = Amende.objects.filter(lecteur=request.user).order_by('-id')
    paiements = Payment.objects.filter(user=request.user).order_by('-date')
    # CrÃ©ation automatique d'une amende pour chaque emprunt en retard non retournÃ©
    for emprunt in emprunts:
        if not emprunt.date_retour_reel:
            emprunt.jours_restants = (emprunt.date_retour_prevue - today).days
            emprunt.jours_retard = max(0, (today - emprunt.date_retour_prevue).days)
            # CrÃ©e l'amende si retard et aucune amende existante pour cet emprunt
            if emprunt.jours_retard > 0 and not Amende.objects.filter(emprunt=emprunt).exists():
                montant = emprunt.jours_retard * 10
                Amende.objects.create(
                    emprunt=emprunt,
                    lecteur=emprunt.lecteur,
                    montant=montant,
                    montant_paye=0,
                    raison=f"Retard de {emprunt.jours_retard} jour(s)",
                    payee=False
                )
        else:
            emprunt.jours_restants = None
            emprunt.jours_retard = None
    # Recharge la liste des amendes aprÃ¨s crÃ©ation Ã©ventuelle
    amendes = Amende.objects.filter(lecteur=request.user).order_by('-id')
    # VÃ©rifier si l'utilisateur a des amendes non payÃ©es pour l'indicateur
    has_amendes = Amende.objects.filter(lecteur=request.user, payee=False).exists()
    
    return render(request, 'library/history.html', {
        'emprunts': emprunts,
        'reservations': reservations,
        'amendes': amendes,
        'paiements': paiements,
        'today': today,
        'has_amendes': has_amendes,  # Pour l'indicateur dans la barre de navigation
    })

@login_required
def annuler_emprunt(request, emprunt_id):
    """Demande de retour d'un emprunt (validation par superuser requise)."""
    emprunt = get_object_or_404(Emprunt, id=emprunt_id, lecteur=request.user)
    if request.method == 'POST':
        emprunt.retour_demande = True
        emprunt.save()
        messages.success(request, "Demande de retour envoyÃ©e. En attente de validation par l'administrateur.")
    return redirect('history')


@staff_member_required
def dashboard(request):
    """Tableau de bord avec statistiques et graphiques pour les administrateurs."""
    current_date = timezone.now().date()
    current_month = timezone.now().month
    current_year = timezone.now().year
    
    # Statistiques gÃ©nÃ©rales
    total_livres = Livre.objects.count()
    
    # Nombre total de livres physiquement disponibles (stock > 0)
    livres_disponibles_physique = Livre.objects.filter(stock__gt=0).count()
    
    # Nombre de réservations payées (qui devraient être converties en emprunts)
    reservations_payees = Reservation.objects.filter(est_payee=True).count()
    
    # Nombre de réservations non payées
    reservations_non_payees = Reservation.objects.filter(est_payee=False).count()
    
    # Nombre total de réservations
    reservations_actives = reservations_payees + reservations_non_payees
    
    # Livres disponibles pour de nouveaux emprunts (stock > 0 et pas de réservation payée)
    livres_disponibles = livres_disponibles_physique
    
    # Emprunts actifs
    emprunts_actifs = Emprunt.objects.filter(est_retourne=False).count()
    
    # Emprunts en retard
    emprunts_retard = Emprunt.objects.filter(
        est_retourne=False,
        date_retour_prevue__lt=current_date
    ).count()
    
    total_amendes = Amende.objects.aggregate(total=Sum('montant'))['total'] or 0
    amendes_non_payees = Amende.objects.filter(payee=False).aggregate(total=Sum('montant'))['total'] or 0
    
    total_utilisateurs = User.objects.count()
    nouveaux_utilisateurs = User.objects.filter(
        date_joined__year=current_year,
        date_joined__month=current_month
    ).count()
    
    # Revenus du mois courant
    revenus_mois = Payment.objects.filter(
        date__year=current_year,
        date__month=current_month,
        is_valid=True
    ).aggregate(total=Sum('amount'))['total'] or 0
    
    # Livres les plus populaires (basÃ© sur le nombre d'emprunts)
    livres_populaires = Livre.objects.annotate(
        nb_emprunts=Count('emprunt')
    ).order_by('-nb_emprunts')[:10]
    
    # Livres les plus rÃ©servÃ©s
    livres_reserves = Livre.objects.annotate(
        nb_reservations=Count('reservation'),
        reservations_payees=Count('reservation', filter=Q(reservation__est_payee=True)),
        reservations_non_payees=Count('reservation', filter=Q(reservation__est_payee=False))
    ).order_by('-nb_reservations')[:10]
    
    # Ajouter les notes moyennes et formater pour l'affichage
    for livre in livres_populaires:
        notes = NotationUtilisateur.objects.filter(livre=livre)
        if notes.exists():
            livre.note = round(notes.aggregate(avg=Avg('note'))['avg'], 1)
        else:
            livre.note = 0
        
        # CrÃ©er les Ã©toiles pour l'affichage
        livre.note_etoiles = range(int(livre.note))
        livre.note_vides = range(5 - int(livre.note))
    
    # Emprunts rÃ©cents
    emprunts_recents = Emprunt.objects.all().order_by('-date_emprunt')[:10]
    
    # DonnÃ©es pour le graphique des catÃ©gories
    categories_data = Livre.objects.values('categorie').annotate(
        count=Count('emprunt')
    ).order_by('-count')
    
    categories = [item['categorie'] for item in categories_data]
    emprunts_par_categorie = [item['count'] for item in categories_data]
    
    # DonnÃ©es pour le graphique d'activitÃ© mensuelle
    mois_noms = []
    emprunts_par_mois = []
    reservations_par_mois = []
    
    # RÃ©cupÃ©rer les donnÃ©es des 6 derniers mois
    for i in range(5, -1, -1):
        # Calculer le mois
        month = current_month - i
        year = current_year
        if month <= 0:
            month += 12
            year -= 1
        
        # Nom du mois
        mois_noms.append(calendar.month_name[month][:3])
        
        # Nombre d'emprunts pour ce mois
        emprunts_count = Emprunt.objects.filter(
            date_emprunt__year=year,
            date_emprunt__month=month
        ).count()
        emprunts_par_mois.append(emprunts_count)
        
        # Nombre de rÃ©servations pour ce mois
        reservations_count = Reservation.objects.filter(
            date_reservation__year=year,
            date_reservation__month=month
        ).count()
        reservations_par_mois.append(reservations_count)
    
    # DonnÃ©es pour les sections CRUD
    # Tous les utilisateurs pour la gestion des utilisateurs
    users = User.objects.all().order_by('-date_joined')
    
    # Tous les livres pour la gestion des livres
    all_livres = Livre.objects.all().order_by('titre')
    
    # Tous les emprunts pour la gestion des emprunts
    all_emprunts = Emprunt.objects.all().order_by('-date_emprunt')
    
    # RÃ©cupÃ©rer les demandes de retour de livres
    demandes_retour = Emprunt.objects.filter(demande_retour=True, est_retourne=False).select_related('livre', 'lecteur').order_by('date_demande_retour')
    
    # Toutes les rÃ©servations pour la gestion des rÃ©servations
    all_reservations = Reservation.objects.all().order_by('-date_reservation')
    
    # Toutes les amendes pour la gestion des amendes
    all_amendes = Amende.objects.all().order_by('-id')
    
    # Tous les paiements pour la gestion des paiements
    all_payments = Payment.objects.all().order_by('-date')
    
    context = {
        'current_date': current_date,
        'total_livres': total_livres,
        'livres_disponibles': livres_disponibles,
        'emprunts_actifs': emprunts_actifs,
        'emprunts_retard': emprunts_retard,
        'reservations_actives': reservations_actives,
        'reservations_payees': reservations_payees,
        'total_amendes': total_amendes,
        'amendes_non_payees': amendes_non_payees,
        'total_utilisateurs': total_utilisateurs,
        'nouveaux_utilisateurs': nouveaux_utilisateurs,
        'revenus_mois': revenus_mois,
        'livres_populaires': livres_populaires,
        'livres_reserves': livres_reserves,
        'emprunts_recents': emprunts_recents,
        'categories': json.dumps(categories),
        'emprunts_par_categorie': emprunts_par_categorie,
        'mois': json.dumps(mois_noms),
        'emprunts_par_mois': emprunts_par_mois,
        'reservations_par_mois': reservations_par_mois,
        # DonnÃ©es pour les sections CRUD
        'users': users,
        'all_livres': all_livres,
        'all_emprunts': all_emprunts,
        'all_reservations': all_reservations,
        'all_amendes': all_amendes,
        'all_payments': all_payments,
        'demandes_retour': demandes_retour,
    }
    
    return render(request, 'library/dashboard.html', context)


@staff_member_required
def dashboard_users(request):
    """Vue pour afficher la section utilisateurs du dashboard."""
    users = User.objects.all().order_by('-date_joined')
    context = {
        'users': users,
    }
    return render(request, 'library/dashboard_users.html', context)


@staff_member_required
def dashboard_books(request):
    """Vue pour afficher la section livres du dashboard."""
    current_date = timezone.now().date()
    all_livres = Livre.objects.all().order_by('titre')
    
    context = {
        'current_date': current_date,
        'all_livres': all_livres,
    }
    return render(request, 'library/dashboard_books.html', context)


@staff_member_required
def dashboard_loans(request):
    """Vue pour afficher la section emprunts du dashboard."""
    # Date actuelle pour les comparaisons
    current_date = timezone.now().date()
    
    # Récupérer tous les emprunts actifs (non retournés)
    all_emprunts = Emprunt.objects.filter(est_retourne=False).order_by('-date_emprunt')
    print(f"Nombre d'emprunts actifs: {all_emprunts.count()}")
    
    # Récupérer les emprunts retournés
    emprunts_retournes = Emprunt.objects.filter(est_retourne=True).order_by('-date_retour_reel')
    print(f"Nombre d'emprunts retournés: {emprunts_retournes.count()}")
    
    # Récupérer uniquement les emprunts avec demande de retour active et non encore retournés
    demandes_retour = Emprunt.objects.filter(demande_retour=True, est_retourne=False).order_by('-date_demande_retour')
    
    # Log détaillé pour débogage
    print(f"Nombre de demandes de retour actives: {demandes_retour.count()}")
    for emprunt in demandes_retour:
        print(f"Emprunt #{emprunt.id}: {emprunt.livre.titre} - {emprunt.lecteur.username} - Demande de retour: {emprunt.demande_retour}")
    
    # Récupérer l'onglet actif depuis les paramètres de l'URL
    active_tab = request.GET.get('tab', 'active-loans')
    
    # Préparer le contexte pour le template
    context = {
        'all_emprunts': all_emprunts,
        'emprunts_retournes': emprunts_retournes,
        'demandes_retour': demandes_retour,
        'current_date': current_date,
        'active_tab': active_tab,
    }
    return render(request, 'library/dashboard_loans.html', context)


@staff_member_required
def dashboard_reservations(request):
    """Vue pour afficher la section rÃ©servations du dashboard."""
    all_reservations = Reservation.objects.all().order_by('-date_reservation')
    
    context = {
        'all_reservations': all_reservations,
    }
    return render(request, 'library/dashboard_reservations.html', context)


@staff_member_required
def emprunt_history(request):
    """Vue pour afficher l'historique des emprunts"""
    # Récupérer tout l'historique des emprunts
    from .models import HistoriqueEmprunt
    historiques = HistoriqueEmprunt.objects.all().select_related('emprunt', 'emprunt__livre', 'emprunt__lecteur', 'utilisateur')
    
    context = {
        'historiques': historiques,
    }
    
    return render(request, 'library/emprunt_history.html', context)

@staff_member_required
def dashboard_reviews(request):
    """Vue pour afficher la section avis du dashboard."""
    all_avis = NotationUtilisateur.objects.all().order_by('-date_notation')
    context = {
        'all_avis': all_avis
    }
    return render(request, 'library/dashboard_reviews.html', context)

@staff_member_required
def dashboard_return_requests(request):
    """Vue pour afficher la section des demandes de retour du dashboard."""
    # Récupérer les emprunts avec des demandes de retour en attente
    # Soit via le modèle RetourLivre, soit via le champ demande_retour
    demandes_retour = Emprunt.objects.filter(
        Q(retours__statut='en_attente') | Q(demande_retour=True)
    ).distinct().order_by('-date_demande_retour', '-retours__date_demande')
    
    # Date actuelle pour les comparaisons
    current_date = timezone.now().date()
    
    context = {
        'demandes_retour': demandes_retour,
        'current_date': current_date,
    }
    return render(request, 'library/dashboard_return_requests.html', context)


@csrf_exempt
def delete_review(request, review_id):
    """Vue pour supprimer un avis"""
    if request.method == 'POST' and request.user.is_staff:
        try:
            avis = NotationUtilisateur.objects.get(id=review_id)
            avis.delete()
            return JsonResponse({'success': True})
        except NotationUtilisateur.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Avis non trouvÃ©'})
        except Exception as e:
            emprunt = Emprunt.objects.get(id=emprunt_id)
            
            # Vérifier si l'emprunt n'est pas déjà retourné
            if emprunt.est_retourne:
                return JsonResponse({'success': False, 'error': 'Ce livre a déjà été retourné'})
            
            # Mettre à jour le statut de l'emprunt
            emprunt.est_retourne = True
            emprunt.date_retour = timezone.now()
            emprunt.demande_retour = False  # Réinitialiser la demande de retour
            emprunt.save()
            
            # Augmenter le stock du livre
            livre = emprunt.livre
            old_stock = livre.stock
            livre.stock += 1
            livre.disponible = True  # Marquer le livre comme disponible
            livre.save()
            
            # Importer la fonction pour traiter les rÃ©servations
            from .signals import process_reservations_for_book
            
            # Traiter les rÃ©servations payÃ©es pour ce livre
            process_reservations_for_book(livre, 1)  # Traiter une unitÃ© retournÃ©e
            
            # VÃ©rifier si le stock a Ã©tÃ© utilisÃ© pour une rÃ©servation payÃ©e
            if livre.stock == old_stock:  # Le stock n'a pas changÃ©, donc pas de rÃ©servation payÃ©e traitÃ©e
                print(f"Aucune rÃ©servation payÃ©e traitÃ©e pour le livre {livre.titre}")
            else:
                print(f"Une rÃ©servation payÃ©e a Ã©tÃ© traitÃ©e pour le livre {livre.titre}")
            
            # Envoyer un email de confirmation au lecteur
            try:
                send_mail(
                    'Confirmation de retour de livre',
                    f'Bonjour {emprunt.lecteur.username},\n\n'
                    f'Nous confirmons le retour du livre "{livre.titre}" le {timezone.now().strftime("%d/%m/%Y")}. '
                    f'Merci d\'avoir utilisÃ© notre bibliothÃ¨que.\n\n'
                    f'Cordialement,\nL\'Ã©quipe BiblioSmart',
                    settings.DEFAULT_FROM_EMAIL,
                    [emprunt.lecteur.email],
                    fail_silently=True,
                )
            except Exception as e:
                print(f"Erreur lors de l'envoi de l'email: {str(e)}")  # Log l'erreur pour dÃ©bogage
            
            return JsonResponse({'success': True})
        except Emprunt.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Emprunt non trouvé'})
        except Exception as e:
            print(f"Erreur lors du retour du livre: {str(e)}")  # Log l'erreur pour débogage
            return JsonResponse({'success': False, 'error': str(e)})
    return JsonResponse({'success': False, 'error': 'Méthode non autorisée'})

@csrf_exempt
def return_book(request, emprunt_id):
    """Vue pour retourner un livre emprunté"""
    if request.method == 'POST' and request.user.is_staff:
        try:
            emprunt = Emprunt.objects.get(id=emprunt_id)
            
            # Vérifier si l'emprunt n'est pas déjà retourné
            if emprunt.est_retourne:
                return JsonResponse({'success': False, 'error': 'Ce livre a déjà été retourné'})
            
            # Mettre à jour le statut de l'emprunt
            emprunt.est_retourne = True
            emprunt.date_retour_reel = timezone.now()
            emprunt.demande_retour = False  # Réinitialiser la demande de retour
            emprunt.save()
            
            # Augmenter le stock du livre
            livre = emprunt.livre
            livre.stock = livre.stock + 1
            livre.disponible = livre.stock > 0  # Mettre à jour la disponibilité
            livre.save()
            
            # Mettre à jour les entrées RetourLivre associées
            retours = RetourLivre.objects.filter(emprunt=emprunt, statut='en_attente')
            for retour in retours:
                retour.statut = 'valide'
                retour.date_validation = timezone.now()
                retour.save()
            
            # Vérifier s'il y a des réservations en attente pour ce livre
            reservations_en_attente = Reservation.objects.filter(
                livre=livre, 
                est_active=True,
                est_notifiee=False,
                est_annulee=False
            ).order_by('date_reservation')
            
            if reservations_en_attente.exists():
                # Notifier le premier utilisateur en file d'attente
                reservation = reservations_en_attente.first()
                reservation.est_notifiee = True
                reservation.date_notification = timezone.now()
                reservation.save()
                
                # Envoyer un email de notification
                try:
                    subject = 'Livre disponible pour emprunt'
                    message = f'Bonjour {reservation.lecteur.username},\n\nLe livre "{livre.titre}" que vous avez réservé est maintenant disponible. Vous avez 48 heures pour venir l\'emprunter à la bibliothèque.\n\nCordialement,\nL\'équipe de la bibliothèque'
                    send_mail(
                        subject,
                        message,
                        'bibliotheque@example.com',
                        [reservation.lecteur.email],
                        fail_silently=True,
                    )
                except Exception as e:
                    print(f"Erreur lors de l'envoi de l'email de notification: {str(e)}")
            
            # Envoyer un email de confirmation au lecteur
            try:
                send_mail(
                    'Retour de livre confirmé',
                    f'Bonjour {emprunt.lecteur.username},\n\n'
                    f'Le retour du livre "{emprunt.livre.titre}" a bien été enregistré.\n\n'
                    f'Cordialement,\nL\'\u00e9quipe de la bibliothèque',
                    settings.DEFAULT_FROM_EMAIL,
                    [emprunt.lecteur.email],
                    fail_silently=True,
                )
            except Exception as e:
                print(f"Erreur lors de l'envoi de l'email: {str(e)}")
            
            return JsonResponse({'success': True, 'message': 'Livre retourné avec succès'})
        except Emprunt.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'Emprunt non trouvé'})
        except Exception as e:
            print(f"Erreur lors du retour du livre: {str(e)}")
            return JsonResponse({'success': False, 'message': f'Erreur lors du retour du livre: {str(e)}'})
    return JsonResponse({'success': False, 'message': 'Méthode non autorisée'}, status=405)

@csrf_exempt
def request_return(request, emprunt_id):
    """Demander le retour d'un livre emprunté"""
    if request.method == 'POST':
        try:
            emprunt = Emprunt.objects.get(id=emprunt_id, lecteur=request.user, est_retourne=False)
            
            # Vérifier si une demande de retour existe déjà
            if emprunt.demande_retour or RetourLivre.objects.filter(emprunt=emprunt, statut='en_attente').exists():
                return JsonResponse({'success': False, 'message': 'Une demande de retour est déjà en cours pour ce livre.'})
            
            # Créer une demande de retour
            print(f"Création d'une demande de retour pour l'emprunt ID: {emprunt.id}")
            emprunt.demande_retour = True
            emprunt.date_demande_retour = timezone.now()
            emprunt.save()
            print(f"Emprunt mis à jour: demande_retour={emprunt.demande_retour}, date_demande_retour={emprunt.date_demande_retour}")
            
            # Créer également une entrée dans RetourLivre pour compatibilité
            retour = RetourLivre.objects.create(
                emprunt=emprunt,
                date_demande=timezone.now(),
                statut='en_attente'
            )
            print(f"RetourLivre créé: ID={retour.id}, statut={retour.statut}, date_demande={retour.date_demande}")
            
            # Vérifier que la demande a bien été créée
            verification = RetourLivre.objects.filter(emprunt=emprunt, statut='en_attente').exists()
            print(f"Vérification de la création de la demande de retour: {verification}")
            
            # Rafraîchir l'objet emprunt depuis la base de données
            emprunt.refresh_from_db()
            print(f"Après refresh: demande_retour={emprunt.demande_retour}, date_demande_retour={emprunt.date_demande_retour}")
            
            # Envoyer un email de notification à l'administrateur
            admins = User.objects.filter(is_staff=True)
            admin_emails = [admin.email for admin in admins if admin.email]
            
            if admin_emails:
                subject = 'Nouvelle demande de retour de livre'
                message = f'L\'utilisateur {request.user.username} a demandé à retourner le livre "{emprunt.livre.titre}". Veuillez traiter cette demande dans le tableau de bord administrateur.'
                send_mail(
                    subject,
                    message,
                    'bibliotheque@example.com',
                    admin_emails,
                    fail_silently=True,
                )
            
            return JsonResponse({'success': True, 'message': 'Votre demande de retour a été enregistrée et sera traitée par un administrateur.'})
        
        except Emprunt.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'Emprunt non trouvé ou vous n\'\u00eates pas autorisé à demander le retour de ce livre.'})
        except Exception as e:
            print(f"Erreur lors de la demande de retour: {str(e)}")
            return JsonResponse({'success': False, 'message': f'Une erreur est survenue: {str(e)}'})
    
    return JsonResponse({'success': False, 'message': 'Méthode non autorisée.'}, status=405)

@staff_member_required
def validate_return(request, emprunt_id):
    """Valider une demande de retour par un administrateur"""
    if request.method == 'POST':
        try:
            # Récupérer l'emprunt concerné
            emprunt = Emprunt.objects.get(id=emprunt_id, est_retourne=False)
            
            # Vérifier que l'emprunt a bien une demande de retour
            if not emprunt.demande_retour and not RetourLivre.objects.filter(emprunt=emprunt, statut='en_attente').exists():
                return JsonResponse({'success': False, 'message': 'Aucune demande de retour trouvée pour cet emprunt.'})
            
            # Marquer l'emprunt comme retourné
            emprunt.est_retourne = True
            emprunt.date_retour_reel = timezone.now().date()
            emprunt.demande_retour = False  # Réinitialiser le flag de demande
            emprunt.save()
            
            # Générer l'amende si nécessaire
            if emprunt.date_retour_reel > emprunt.date_retour_prevue:
                jours_retard = (emprunt.date_retour_reel - emprunt.date_retour_prevue).days
                montant = 10 * jours_retard  # 10 MAD par jour de retard
                if not Amende.objects.filter(emprunt=emprunt).exists():
                    Amende.objects.create(
                        emprunt=emprunt,
                        lecteur=emprunt.lecteur,
                        montant=montant,
                        raison=f"Retard de {jours_retard} jour(s)",
                        payee=False
                    )
            
            # Mettre à jour le stock du livre
            livre = emprunt.livre
            livre.stock += 1
            livre.disponible = True
            livre.save()
            
            # Mettre à jour les entrées RetourLivre associées
            retours = RetourLivre.objects.filter(emprunt=emprunt, statut='en_attente')
            for retour in retours:
                retour.statut = 'valide'
                retour.date_validation = timezone.now()
                retour.save()
                
            # Ajouter une entrée dans l'historique
            try:
                from .models import HistoriqueEmprunt
                HistoriqueEmprunt.objects.create(
                    emprunt=emprunt,
                    action='retour_valide',
                    date_action=timezone.now(),
                    commentaire=f"Retour validé par {request.user.username}",
                    utilisateur=request.user
                )
                print(f"Historique créé pour le retour de l'emprunt #{emprunt.id}")
            except Exception as e:
                print(f"Erreur lors de la création de l'historique: {str(e)}")
            
            # Vérifier s'il y a des réservations en attente pour ce livre
            reservations_en_attente = Reservation.objects.filter(
                livre=livre, 
                est_active=True,
                est_notifiee=False,
                est_annulee=False
            ).order_by('date_reservation')
            
            if reservations_en_attente.exists():
                # Attribuer automatiquement le livre au premier utilisateur en file d'attente
                reservation = reservations_en_attente.first()
                lecteur = reservation.lecteur
                
                # Créer un nouvel emprunt pour le lecteur
                from datetime import timedelta
                date_retour_prevue = timezone.now().date() + timedelta(days=7)  # 7 jours d'emprunt
                
                nouvel_emprunt = Emprunt.objects.create(
                    livre=livre,
                    lecteur=lecteur,
                    date_emprunt=timezone.now().date(),
                    date_retour_prevue=date_retour_prevue,
                    est_retourne=False
                )
                
                # Décrémenter le stock du livre (qui vient d'être incrémenté par le retour)
                livre.stock -= 1
                if livre.stock == 0:
                    livre.disponible = False
                livre.save()
                
                # Marquer la réservation comme traitée
                reservation.est_active = False
                reservation.est_notifiee = True
                reservation.date_notification = timezone.now()
                reservation.save()
                
                # Ajouter une entrée dans l'historique pour le nouvel emprunt
                try:
                    HistoriqueEmprunt.objects.create(
                        emprunt=nouvel_emprunt,
                        action='emprunt',
                        date_action=timezone.now(),
                        commentaire=f"Emprunt automatique suite à réservation",
                        utilisateur=request.user
                    )
                except Exception as e:
                    print(f"Erreur lors de la création de l'historique pour le nouvel emprunt: {str(e)}")
                
                # Envoyer un email de notification
                subject = 'Livre attribué automatiquement suite à votre réservation'
                message = f'Bonjour {lecteur.username},\n\nLe livre "{livre.titre}" que vous avez réservé vous a été attribué automatiquement suite à son retour. Votre emprunt est enregistré jusqu\'au {date_retour_prevue.strftime("%d/%m/%Y")}.\n\nCordialement,\nL\'équipe de la bibliothèque'
                send_mail(
                    subject,
                    message,
                    'bibliotheque@example.com',
                    [lecteur.email],
                    fail_silently=True,
                )
            
            # Rediriger vers la page du tableau de bord des emprunts
            from django.contrib import messages
            from django.shortcuts import redirect
            messages.success(request, 'Retour validé avec succès.')
            return redirect('dashboard_loans')
            
        except Emprunt.DoesNotExist:
            from django.contrib import messages
            from django.shortcuts import redirect
            messages.error(request, 'Emprunt non trouvé.')
            return redirect('dashboard_loans')
        except Exception as e:
            from django.contrib import messages
            from django.shortcuts import redirect
            messages.error(request, f'Erreur lors de la validation du retour: {str(e)}')
            return redirect('dashboard_loans')
    
    from django.shortcuts import redirect
    return redirect('dashboard')

@staff_member_required
def validate_return_simple(request, emprunt_id):
    """Version simplifiée de la validation de retour qui se concentre uniquement sur la mise à jour du champ retour_valide_admin."""
    try:
        # Récupérer l'emprunt
        emprunt = Emprunt.objects.get(id=emprunt_id)
        
        # Mettre à jour les champs importants
        emprunt.est_retourne = True
        emprunt.retour_valide_admin = True
        emprunt.date_retour_reel = timezone.now().date()
        emprunt.save()
        
        # Mettre à jour le stock du livre
        livre = emprunt.livre
        livre.stock += 1
        livre.disponible = True
        livre.save()
        
        messages.success(request, f'Le retour du livre "{livre.titre}" a été validé avec succès.')
    except Exception as e:
        messages.error(request, f'Erreur: {str(e)}')
    
    return redirect('dashboard')

@staff_member_required
def refuse_return(request, emprunt_id):
    """Refuser une demande de retour par un administrateur"""
    if request.method == 'POST':
        try:
            # Récupérer l'emprunt concerné
            emprunt = Emprunt.objects.get(id=emprunt_id, est_retourne=False)
            
            # Vérifier que l'emprunt a bien une demande de retour
            if not emprunt.demande_retour and not RetourLivre.objects.filter(emprunt=emprunt, statut='en_attente').exists():
                return JsonResponse({'success': False, 'message': 'Aucune demande de retour trouvée pour cet emprunt.'})
            
            # Réinitialiser le flag de demande de retour
            emprunt.demande_retour = False
            emprunt.date_demande_retour = None
            emprunt.save()
            
            # Mettre à jour les entrées RetourLivre associées
            retours = RetourLivre.objects.filter(emprunt=emprunt, statut='en_attente')
            for retour in retours:
                retour.statut = 'refuse'
                retour.date_traitement = timezone.now()
                retour.save()
            
            # Ajouter une entrée dans l'historique
            try:
                from .models import HistoriqueEmprunt
                HistoriqueEmprunt.objects.create(
                    emprunt=emprunt,
                    action='retour_refuse',
                    date_action=timezone.now(),
                    commentaire=f"Retour refusé par {request.user.username}",
                    utilisateur=request.user
                )
                print(f"Historique créé pour le refus de retour de l'emprunt #{emprunt.id}")
            except Exception as e:
                print(f"Erreur lors de la création de l'historique: {str(e)}")
            
            # Envoyer un email de notification au lecteur
            subject = 'Demande de retour refusée'
            message = f'Bonjour {emprunt.lecteur.username},\n\nVotre demande de retour pour le livre "{emprunt.livre.titre}" a été refusée. Veuillez contacter la bibliothèque pour plus d\'informations.\n\nCordialement,\nL\'équipe de la bibliothèque'
            send_mail(
                subject,
                message,
                'bibliotheque@example.com',
                [emprunt.lecteur.email],
                fail_silently=True,
            )
            
            # Rediriger vers la page du tableau de bord des emprunts
            from django.contrib import messages
            from django.shortcuts import redirect
            messages.success(request, 'Demande de retour refusée avec succès.')
            return redirect('dashboard_loans')
            
        except Emprunt.DoesNotExist:
            from django.contrib import messages
            from django.shortcuts import redirect
            messages.error(request, 'Emprunt non trouvé.')
            return redirect('dashboard_loans')
        except Exception as e:
            from django.contrib import messages
            from django.shortcuts import redirect
            messages.error(request, f'Erreur lors du refus de la demande: {str(e)}')
            return redirect('dashboard_loans')
    
    from django.shortcuts import redirect
    return redirect('dashboard_loans')

# Cette fonction a été supprimée car elle était dupliquée
# La version correcte se trouve plus haut dans le fichier

@staff_member_required
def valider_retour_livre(request):
    """Vue pour valider ou refuser une demande de retour de livre via formulaire traditionnel"""
    if request.method == 'POST':
        emprunt_id = request.POST.get('empruntId')
        action = request.POST.get('action')
        
        try:
            emprunt = Emprunt.objects.get(id=emprunt_id)
            
            if action == 'valider':
                # VÃ©rifier si l'emprunt n'est pas dÃ©jÃ  retournÃ©
                if emprunt.est_retourne:
                    messages.error(request, 'Ce livre a dÃ©jÃ  Ã©tÃ© retournÃ©')
                    return redirect('dashboard_books')
                
                # Mettre Ã  jour le statut de l'emprunt
                emprunt.est_retourne = True
                emprunt.date_retour = timezone.now()
                emprunt.demande_retour = False  # RÃ©initialiser la demande de retour
                emprunt.save()
                
                # Augmenter le stock du livre
                livre = emprunt.livre
                old_stock = livre.stock
                livre.stock += 1
                livre.disponible = True  # Marquer le livre comme disponible
                livre.save()
                
                # Importer la fonction pour traiter les rÃ©servations
                from .signals import process_reservations_for_book
                
                # Traiter les rÃ©servations payÃ©es pour ce livre
                process_reservations_for_book(livre, 1)  # Traiter une unitÃ© retournÃ©e
                
                # Envoyer un email de confirmation au lecteur
                try:
                    send_mail(
                        'Confirmation de retour de livre',
                        f'Bonjour {emprunt.lecteur.username},\n\n'
                        f'Nous confirmons le retour du livre "{livre.titre}" le {timezone.now().strftime("%d/%m/%Y")}. '
                        f'Merci d\'avoir utilisÃ© notre bibliothÃ¨que.\n\n'
                        f'Cordialement,\nL\'Ã©quipe BiblioSmart',
                        settings.DEFAULT_FROM_EMAIL,
                        [emprunt.lecteur.email],
                        fail_silently=True,
                    )
                except Exception as e:
                    print(f"Erreur lors de l'envoi de l'email: {str(e)}")  # Log l'erreur pour dÃ©bogage
                
                messages.success(request, f'Le livre "{livre.titre}" a Ã©tÃ© retournÃ© avec succÃ¨s')
            
            elif action == 'refuser':
                # VÃ©rifier si l'emprunt a une demande de retour
                if not emprunt.demande_retour:
                    messages.error(request, 'Cet emprunt n\'a pas de demande de retour active')
                    return redirect('dashboard_books')
                
                # Mettre Ã  jour le statut de la demande de retour
                emprunt.demande_retour = False
                emprunt.date_demande_retour = None
                emprunt.save()
                
                # Envoyer un email d'information au lecteur
                try:
                    send_mail(
                        'Demande de retour refusÃ©e',
                        f'Bonjour {emprunt.lecteur.username},\n\n'
                        f'Votre demande de retour pour le livre "{emprunt.livre.titre}" a Ã©tÃ© refusÃ©e. '
                        f'Veuillez contacter la bibliothÃ¨que pour plus d\'informations.\n\n'
                        f'Cordialement,\nL\'Ã©quipe BiblioSmart',
                        settings.DEFAULT_FROM_EMAIL,
                        [emprunt.lecteur.email],
                        fail_silently=True,
                    )
                except Exception as e:
                    print(f"Erreur lors de l'envoi de l'email: {str(e)}")  # Log l'erreur pour dÃ©bogage
                
                messages.success(request, f'La demande de retour pour le livre "{emprunt.livre.titre}" a Ã©tÃ© refusÃ©e')
            
            else:
                messages.error(request, 'Action non reconnue')
        
        except Emprunt.DoesNotExist:
            messages.error(request, 'Emprunt non trouvÃ©')
        except Exception as e:
            messages.error(request, f'Erreur: {str(e)}')
    
    # Rediriger vers la section livres du dashboard
    return redirect('dashboard_books')


@csrf_exempt
def ajouter_livre(request):
    """Vue pour ajouter, modifier, récupérer ou supprimer un livre"""
    # Vérifier si le répertoire media existe, sinon le créer
    import os
    import shutil
    from django.conf import settings
    from django.shortcuts import redirect
    from django.contrib import messages
    from django.core.files.storage import default_storage
    from django.core.files.base import ContentFile
    import uuid
    
    media_root = settings.MEDIA_ROOT
    livres_dir = os.path.join(media_root, 'livres')
    photos_dir = os.path.join(media_root, 'livres', 'photos')
    
    # S'assurer que les répertoires existent et ont les permissions correctes
    for directory in [media_root, livres_dir, photos_dir]:
        if not os.path.exists(directory):
            os.makedirs(directory, exist_ok=True)
            # Donner les permissions complètes au répertoire
            try:
                os.chmod(directory, 0o777)
            except Exception as e:
                print(f"Erreur lors de la modification des permissions: {str(e)}")
    
    print(f"Chemins des répertoires: media_root={media_root}, livres_dir={livres_dir}, photos_dir={photos_dir}")
    print(f"Méthode de la requête: {request.method}")
    print(f"FILES: {request.FILES}")
    print(f"POST: {request.POST}")
    
    # GET pour récupérer les détails d'un livre ou afficher le formulaire d'ajout
    if request.method == 'GET':
        book_id = request.GET.get('book_id')
        livre = None
        action = request.GET.get('action', 'add')  # Par défaut, l'action est d'ajouter
        
        if book_id:
            try:
                livre = Livre.objects.get(id=book_id)
                # Si c'est une requête AJAX pour le formulaire, renvoyer le HTML
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest' and request.GET.get('ajax') == 'form':
                    # Préparer le contexte pour le template du formulaire
                    categories = ['Roman', 'Science-fiction', 'Fantastique', 'Policier', 'Biographie', 'Histoire', 'Philosophie', 'Sciences', 'Art', 'Cuisine', 'Voyage', 'Jeunesse', 'BD', 'Autre']
                    context = {
                        'livre': livre,
                        'categories': categories,
                        'action': 'edit'
                    }
                    # Renvoyer le HTML du formulaire
                    return render(request, 'library/ajouter_livre.html', context)
                # Si c'est une requête AJAX standard, renvoyer les détails du livre en JSON
                elif request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({
                        'success': True,
                        'livre': {
                            'id': livre.id,
                            'titre': livre.titre,
                            'auteur': livre.auteur,
                            'categorie': livre.categorie,
                            'stock': livre.stock,
                            'prix': livre.prix,
                            'disponible': livre.disponible,
                            'photo_url': livre.photo.url if livre.photo else None
                        }
                    })
            except Livre.DoesNotExist:
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest' and request.GET.get('ajax') == 'form':
                    # Renvoyer un message d'erreur HTML pour les requêtes de formulaire
                    return HttpResponse('<div class="alert alert-danger">Livre non trouvé.</div>')
                elif request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({
                        'success': False,
                        'message': 'Livre non trouvé.'
                    })
                messages.error(request, 'Livre non trouvé.')
            except Exception as e:
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({
                        'success': False,
                        'message': f'Erreur: {str(e)}'
                    })
                messages.error(request, f'Erreur: {str(e)}')
        
        # Préparer le contexte pour le template
        categories = ['Roman', 'Science-fiction', 'Fantastique', 'Policier', 'Biographie', 'Histoire', 'Philosophie', 'Sciences', 'Art', 'Cuisine', 'Voyage', 'Jeunesse', 'BD', 'Autre']
        
        context = {
            'livre': livre,
            'categories': categories,
            'action': action
        }
        
        # Si c'est une requête AJAX pour le formulaire, renvoyer le HTML du formulaire
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest' and request.GET.get('ajax') == 'form':
            return render(request, 'library/ajouter_livre.html', context)
        
        # Sinon, afficher la page complète
        return render(request, 'library/ajouter_livre.html', context)
    
    # POST pour ajouter, modifier ou supprimer un livre
    elif request.method == 'POST':
        # Afficher les informations de débogage pour vérifier les fichiers
        print("FILES:", request.FILES)
        print("POST:", request.POST)
        try:
            # Récupérer les données du formulaire
            book_id = request.POST.get('bookId', '')
            form_action = request.POST.get('formAction', 'add')
            
            # Afficher les informations de débogage pour vérifier les paramètres
            print(f"Action: {form_action}, Book ID: {book_id}")
            if form_action == 'edit' and not book_id:
                print("ATTENTION: Action d'édition spécifiée mais aucun ID de livre fourni!")
                # Essayer de récupérer l'ID du livre d'une autre manière
                book_id = request.POST.get('book_id', '')  # Essayer un autre nom de paramètre
                print(f"Tentative de récupération alternative de l'ID: {book_id}")
            
            # Pour les requêtes AJAX, vérifier si c'est une requête AJAX
            is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest' or 'application/json' in request.headers.get('Content-Type', '')
            
            # Gestion de la suppression
            if form_action == 'delete' and book_id:
                try:
                    livre = Livre.objects.get(id=book_id)
                    titre = livre.titre  # Sauvegarder le titre pour le message
                    livre.delete()
                    
                    # Pour les soumissions de formulaire traditionnelles, rediriger vers le dashboard
                    if request.headers.get('X-Requested-With') != 'XMLHttpRequest':
                        messages.success(request, f'Livre "{titre}" supprimé avec succès!')
                        return redirect('dashboard')
                    
                    # Pour les requêtes AJAX, renvoyer une réponse JSON
                    return JsonResponse({
                        'success': True,
                        'message': f'Livre "{titre}" supprimé avec succès!'
                    })
                except Livre.DoesNotExist:
                    # Pour les soumissions de formulaire traditionnelles, rediriger vers le dashboard
                    if request.headers.get('X-Requested-With') != 'XMLHttpRequest':
                        messages.error(request, 'Livre non trouvé.')
                        return redirect('dashboard')
                    
                    # Pour les requêtes AJAX, renvoyer une réponse JSON
                    return JsonResponse({
                        'success': False,
                        'message': 'Livre non trouvé.'
                    })
                except Exception as e:
                    # Pour les soumissions de formulaire traditionnelles, rediriger vers le dashboard
                    if request.headers.get('X-Requested-With') != 'XMLHttpRequest':
                        messages.error(request, f'Erreur lors de la suppression: {str(e)}')
                        return redirect('dashboard')
                    
                    # Pour les requêtes AJAX, renvoyer une réponse JSON
                    return JsonResponse({
                        'success': False,
                        'message': f'Erreur lors de la suppression: {str(e)}'
                    })
            
            # Données communes pour l'ajout et la modification
            titre = request.POST.get('titre', '')
            auteur = request.POST.get('auteur', '')
            isbn = request.POST.get('isbn', '')
            annee_publication = request.POST.get('annee_publication', None)
            categorie = request.POST.get('categorie', '')
            stock = request.POST.get('stock', 1)
            prix = request.POST.get('prix', 0)
            
            # Convertir l'année de publication en entier si elle est fournie
            if annee_publication and annee_publication.strip():
                try:
                    annee_publication = int(annee_publication)
                except ValueError:
                    annee_publication = None
            else:
                annee_publication = None
            
            # Vérifier si c'est un ajout ou une modification
            if form_action == 'add':
                # Vérifier que tous les champs obligatoires sont remplis
                if not titre or not auteur or not categorie or 'photo' not in request.FILES:
                    return JsonResponse({
                        'success': False,
                        'message': 'Veuillez remplir tous les champs obligatoires.'
                    })
                
                # Créer un nouveau livre sans la photo
                livre = Livre(
                    titre=titre,
                    auteur=auteur,
                    isbn=isbn if isbn else None,
                    annee_publication=annee_publication,
                    categorie=categorie,
                    stock=int(stock),
                    prix=float(prix),
                    disponible=int(stock) > 0
                )
                
                # Sauvegarder d'abord le livre sans la photo
                livre.save()
                
                # Gérer l'upload de la photo
                if 'photo' in request.FILES and request.FILES['photo']:
                    photo_file = request.FILES['photo']
                    print(f"Traitement de la photo pour nouveau livre: {photo_file.name}, taille: {photo_file.size} bytes")
                    
                    try:
                        # Générer un nom de fichier unique
                        file_extension = os.path.splitext(photo_file.name)[1].lower()
                        # On ne peut pas utiliser l'ID du livre car il n'est pas encore créé
                        unique_filename = f"livre_new_{uuid.uuid4().hex[:10]}{file_extension}"
                        
                        # Chemin complet pour le fichier
                        file_path = os.path.join('livres', 'photos', unique_filename)
                        print(f"Nouveau chemin de fichier: {file_path}")
                        
                        # Sauvegarder le fichier
                        # Lire le contenu du fichier une seule fois
                        file_content = ContentFile(photo_file.read())
                        saved_path = default_storage.save(file_path, file_content)
                        print(f"Fichier sauvegardé à: {saved_path}")
                        
                        # Assigner le chemin relatif aux deux champs d'image du modèle
                        livre.photo = saved_path
                        livre.image = saved_path  # Mettre à jour également le champ image pour la compatibilité avec les templates
                        print(f"Chemin de photo assigné au nouveau livre: {livre.photo}")
                    except Exception as e:
                        print(f"Erreur lors du traitement de la photo: {str(e)}")
                        pass
                    livre.save()
                    
                    print(f"Livre enregistré avec ID: {livre.id}, photo: {livre.photo}")
                    if livre.photo:
                        try:
                            print(f"Chemin de la photo: {livre.photo.path}")
                            print(f"URL de la photo: {livre.photo.url}")
                        except Exception as e:
                            print(f"Erreur lors de l'accès au chemin/URL de la photo: {str(e)}")
                else:
                    print("Aucune photo fournie dans la requête")
                
                # Vérifier s'il y a des réservations en attente pour ce livre
                # Cela peut arriver si le livre a été supprimé puis rajouté
                if livre.stock > 0:
                    # Importer la fonction pour traiter les réservations
                    from .signals import process_reservations_for_book
                    # Traiter les réservations pour les nouvelles unités
                    print(f"Nouveau livre ajouté avec {livre.stock} unités en stock, vérification des réservations...")
                    process_reservations_for_book(livre, livre.stock)
                    
                # Pour les soumissions de formulaire traditionnelles, rediriger vers le dashboard
                if request.headers.get('X-Requested-With') != 'XMLHttpRequest':
                    messages.success(request, 'Livre ajouté avec succès!')
                    return redirect('dashboard')
                
                # Pour les requêtes AJAX, renvoyer une réponse JSON
                return JsonResponse({
                    'success': True,
                    'message': 'Livre ajouté avec succès!',
                    'livre_id': livre.id,
                    'titre': livre.titre,
                    'auteur': livre.auteur,
                    'isbn': livre.isbn,
                    'annee_publication': livre.annee_publication,
                    'categorie': livre.categorie,
                    'stock': livre.stock,
                    'prix': livre.prix,
                    'photo_url': livre.photo.url if livre.photo else None
                })
                
            elif form_action == 'edit' and book_id:
                # Récupérer le livre à modifier
                try:
                    livre = Livre.objects.get(id=book_id)
                except Livre.DoesNotExist:
                    return JsonResponse({
                        'success': False,
                        'message': 'Livre non trouvé'
                    })
                except Exception as e:
                    print(f"Erreur lors de la récupération du livre: {str(e)}")
                    return JsonResponse({
                        'success': False,
                        'message': f'Erreur lors de la récupération du livre: {str(e)}'
                    })
                
                # Afficher des informations de débogage détaillées
                print(f"\n=== MODIFICATION DE LIVRE ===\nID: {book_id}\nTitre: {titre}\nAuteur: {auteur}\nCatégorie: {categorie}\nStock: {stock}\nPrix: {prix}\n")
                print(f"Livre trouvé: {livre.id} - {livre.titre}")
                
                try:
                    # Mettre à jour uniquement les champs fournis
                    if titre:
                        livre.titre = titre
                        print(f"Titre mis à jour: {titre}")
                    if auteur:
                        livre.auteur = auteur
                        print(f"Auteur mis à jour: {auteur}")
                    # Mettre à jour l'ISBN (peut être vide)
                    livre.isbn = isbn if isbn else None
                    print(f"ISBN mis à jour: {isbn}")
                    # Mettre à jour l'année de publication
                    livre.annee_publication = annee_publication
                    print(f"Année de publication mise à jour: {annee_publication}")
                    if categorie:
                        livre.categorie = categorie
                        print(f"Catégorie mise à jour: {categorie}")
                    if stock:
                        # Vérifier si le stock augmente
                        old_stock = livre.stock
                        new_stock = int(stock)
                        stock_increase = max(0, new_stock - old_stock)
                        
                        livre.stock = new_stock
                        livre.disponible = livre.stock > 0
                        print(f"Stock mis à jour: {old_stock} -> {new_stock}")
                        
                        # Si le stock a augmenté et qu'il y a des réservations en attente
                        if stock_increase > 0:
                            print(f"Stock augmenté de {stock_increase} unités pour le livre {livre.titre}")
                            # Importer la fonction pour traiter les réservations
                            from .signals import process_reservations_for_book
                            # Traiter les réservations pour les nouvelles unités
                            process_reservations_for_book(livre, stock_increase)
                    if prix:
                        livre.prix = float(prix)
                        print(f"Prix mis à jour: {prix}")
                    
                    # Mettre à jour la photo si fournie
                    if 'photo' in request.FILES:
                        photo_file = request.FILES['photo']
                        print(f"Photo reçue pour mise à jour: {photo_file.name}, taille: {photo_file.size} bytes")
                        
                        # Gérer la photo dans un seul bloc try/except
                        try:
                            # Supprimer l'ancienne photo si elle existe
                            if livre.photo and os.path.exists(livre.photo.path):
                                os.remove(livre.photo.path)
                            
                            # Générer un nom de fichier unique
                            file_extension = os.path.splitext(photo_file.name)[1].lower()
                            unique_filename = f"livre_{livre.id}_{uuid.uuid4().hex[:8]}{file_extension}"
                            file_path = os.path.join('livres', 'photos', unique_filename)
                            
                            # Sauvegarder le fichier
                            file_content = ContentFile(photo_file.read())
                            saved_path = default_storage.save(file_path, file_content)
                            livre.photo = saved_path
                            print(f"Photo sauvegardée: {livre.photo}")
                        except Exception as e:
                            print(f"Erreur lors du traitement de la photo: {str(e)}")
                            livre.photo = None
                    
                    # Sauvegarder le livre
                    livre.save()
                    
                    # Pour les soumissions de formulaire traditionnelles
                    if request.headers.get('X-Requested-With') != 'XMLHttpRequest':
                        messages.success(request, 'Livre modifié avec succès!')
                        return redirect('dashboard')
                    
                    # Pour les requêtes AJAX
                    photo_url = livre.photo.url if livre.photo else None
                    return JsonResponse({
                        'success': True,
                        'message': 'Livre modifié avec succès!',
                        'livre': {
                            'id': livre.id,
                            'titre': livre.titre,
                            'auteur': livre.auteur,
                            'categorie': livre.categorie,
                            'stock': livre.stock,
                            'prix': livre.prix,
                            'disponible': livre.disponible,
                            'photo_url': photo_url
                        }
                    })
                except (Livre.DoesNotExist, Exception) as e:
                    error_message = 'Livre non trouvé' if isinstance(e, Livre.DoesNotExist) else f'Erreur lors de la sauvegarde du livre: {str(e)}'
                    if isinstance(e, Exception) and not isinstance(e, Livre.DoesNotExist):
                        print(f"Erreur lors de la sauvegarde du livre: {str(e)}")
                    return JsonResponse({
                        'success': False,
                        'message': error_message
                    })
        except Livre.DoesNotExist:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': False,
                    'message': 'Livre non trouvé'
                })
            messages.error(request, 'Livre non trouvé')
            return redirect('dashboard')
        except Exception as e:
            error_message = f'Erreur lors du traitement du formulaire: {str(e)}'
            print(error_message)
            
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': False,
                    'message': error_message
                })
            
            messages.error(request, error_message)
            return redirect('dashboard')
                
    # Si on arrive ici, c'est qu'aucune action n'a été spécifiée
    return JsonResponse({
        'success': False,
        'message': 'Action non spécifiée'
    })

# API pour les utilisateurs
# Vue spécifique pour la modification des livres
@login_required
def modifier_livre(request, livre_id):
    """Vue dédiée à la modification d'un livre"""
    # Importer les modules nécessaires
    import os
    import uuid
    from django.core.files.storage import default_storage
    
    # Récupérer le livre à modifier
    try:
        livre = get_object_or_404(Livre, id=livre_id)
    except Exception as e:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': False,
                'message': f'Livre non trouvé: {str(e)}'
            })
        messages.error(request, f'Livre non trouvé: {str(e)}')
        return redirect('dashboard')
    
    # Traitement du formulaire POST
    if request.method == 'POST':
        print(f"Modification du livre ID: {livre_id}")
        print(f"Données POST: {request.POST}")
        print(f"Fichiers: {request.FILES}")
        
        try:
            # Récupérer les données du formulaire
            titre = request.POST.get('titre', '')
            auteur = request.POST.get('auteur', '')
            categorie = request.POST.get('categorie', '')
            stock = request.POST.get('stock', 1)
            prix = request.POST.get('prix', 0)
            
            # Mettre à jour les champs du livre
            if titre:
                livre.titre = titre
            if auteur:
                livre.auteur = auteur
            if categorie:
                livre.categorie = categorie
            if stock:
                # Vérifier si le stock augmente
                old_stock = livre.stock
                new_stock = int(stock)
                stock_increase = max(0, new_stock - old_stock)
                
                livre.stock = new_stock
                livre.disponible = livre.stock > 0
                
                # Si le stock a augmenté et qu'il y a des réservations en attente
                if stock_increase > 0:
                    from .signals import process_reservations_for_book
                    process_reservations_for_book(livre, stock_increase)
            if prix:
                livre.prix = float(prix)
            
            # Mettre à jour la photo si fournie
            if 'photo' in request.FILES and request.FILES['photo']:
                photo_file = request.FILES['photo']
                print(f"Traitement de la photo: {photo_file.name}, taille: {photo_file.size} bytes")
                
                # Supprimer l'ancienne photo si elle existe
                if livre.photo:
                    try:
                        old_path = livre.photo.path
                        print(f"Ancienne photo path: {old_path}")
                        if os.path.exists(old_path):
                            os.remove(old_path)
                            print(f"Ancienne photo supprimée: {old_path}")
                        else:
                            print(f"Ancienne photo introuvable: {old_path}")
                    except Exception as e:
                        print(f"Erreur lors de la suppression de l'ancienne photo: {str(e)}")
                
                # Générer un nom de fichier unique
                file_extension = os.path.splitext(photo_file.name)[1].lower()
                unique_filename = f"livre_{livre.id}_{uuid.uuid4().hex[:8]}{file_extension}"
                
                # Chemin complet pour le fichier
                file_path = os.path.join('livres', 'photos', unique_filename)
                print(f"Nouveau chemin de fichier: {file_path}")
                
                # Sauvegarder le fichier
                saved_path = default_storage.save(file_path, photo_file)
                print(f"Fichier sauvegardé à: {saved_path}")
                
                # Assigner le chemin relatif aux deux champs d'image du modèle
                livre.photo = saved_path
                livre.image = saved_path  # Mettre à jour également le champ image pour la compatibilité avec les templates
            
            # Sauvegarder les modifications
            livre.save()
            print(f"Livre mis à jour avec succès! ID: {livre.id}, Titre: {livre.titre}")
            
            # Réponse en fonction du type de requête
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.POST.get('is_ajax') == 'true':
                # Pour les requêtes AJAX, renvoyer une réponse JSON
                return JsonResponse({
                    'success': True,
                    'message': 'Livre modifié avec succès!',
                    'livre': {
                        'id': livre.id,
                        'titre': livre.titre,
                        'auteur': livre.auteur,
                        'categorie': livre.categorie,
                        'stock': livre.stock,
                        'prix': livre.prix,
                        'disponible': livre.disponible,
                        'photo_url': livre.photo.url if livre.photo else None
                    }
                })
            else:
                # Pour les soumissions de formulaire traditionnelles, rediriger vers le dashboard
                messages.success(request, 'Livre modifié avec succès!')
                return redirect('dashboard')
                
        except Exception as e:
            print(f"Erreur lors de la modification du livre: {str(e)}")
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.POST.get('is_ajax') == 'true':
                return JsonResponse({
                    'success': False,
                    'message': f'Erreur lors de la modification du livre: {str(e)}'
                })
            messages.error(request, f'Erreur lors de la modification du livre: {str(e)}')
            return redirect('dashboard')
    
    # Affichage du formulaire GET
    categories = ['Roman', 'Science-fiction', 'Fantastique', 'Policier', 'Biographie', 'Histoire', 'Philosophie', 'Sciences', 'Art', 'Cuisine', 'Voyage', 'Jeunesse', 'BD', 'Autre']
    
    context = {
        'livre': livre,
        'categories': categories,
        'action': 'edit'
    }
    
    return render(request, 'library/ajouter_livre.html', context)

@csrf_exempt
def api_users(request, user_id=None):
    """API pour récupérer les détails d'un utilisateur"""
    if request.method == 'GET':
        try:
            user = User.objects.get(id=user_id)
            return JsonResponse({
                'success': True,
                'user': {
                    'id': user.id,
                    'username': user.username,
                    'email': user.email,
                    'date_joined': user.date_joined.strftime('%d/%m/%Y'),
                    'is_superuser': user.is_superuser,
                    'is_active': user.is_active
                }
            })
        except User.DoesNotExist:
            return JsonResponse({
                'success': False,
                'message': 'Utilisateur non trouvé.'
            })
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'Erreur: {str(e)}'
            })
    return JsonResponse({
        'success': False,
        'message': 'Méthode non autorisée.'
    })

@csrf_exempt
def api_users_add(request):
    """API pour ajouter un utilisateur"""
    if request.method == 'POST':
        try:
            username = request.POST.get('username')
            email = request.POST.get('email')
            password = request.POST.get('password')
            role = request.POST.get('role', 'reader')  # Par défaut, l'utilisateur est un lecteur
            
            # Vérifier si l'utilisateur existe déjà
            if User.objects.filter(username=username).exists():
                return JsonResponse({
                    'success': False,
                    'message': 'Ce nom d\'utilisateur est déjà utilisé.'
                })
            
            if User.objects.filter(email=email).exists():
                return JsonResponse({
                    'success': False,
                    'message': 'Cette adresse email est déjà utilisée.'
                })
            
            # Créer l'utilisateur
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password
            )
            
            # Définir les permissions selon le rôle
            if role == 'admin':
                user.is_staff = True
                user.is_superuser = True
            
            user.save()
            
            return JsonResponse({
                'success': True,
                'message': 'Utilisateur ajouté avec succès!',
                'user_id': user.id
            })
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'Erreur lors de l\'ajout de l\'utilisateur: {str(e)}'
            })
    return JsonResponse({
        'success': False,
        'message': 'Méthode non autorisée.'
    })

@csrf_exempt
def api_users_edit(request, user_id):
    """API pour modifier un utilisateur"""
    if request.method == 'POST':
        try:
            user = User.objects.get(id=user_id)
            
            username = request.POST.get('username')
            email = request.POST.get('email')
            role = request.POST.get('role')
            status = request.POST.get('status')
            
            # Vérifier si le nom d'utilisateur est déjà utilisé par un autre utilisateur
            if username != user.username and User.objects.filter(username=username).exists():
                return JsonResponse({
                    'success': False,
                    'message': 'Ce nom d\'utilisateur est déjà utilisé.'
                })
            
            # Vérifier si l'email est déjà utilisé par un autre utilisateur
            if email != user.email and User.objects.filter(email=email).exists():
                return JsonResponse({
                    'success': False,
                    'message': 'Cette adresse email est déjà utilisée.'
                })
            
            # Mettre à jour les informations de l'utilisateur
            user.username = username
            user.email = email
            
            # Mettre à jour le rôle
            if role == 'admin':
                user.is_staff = True
                user.is_superuser = True
            else:  # role == 'reader'
                user.is_staff = False
                user.is_superuser = False
            
            # Mettre à jour le statut
            user.is_active = (status == 'active')
            
            user.save()
            
            return JsonResponse({
                'success': True,
                'message': 'Utilisateur modifié avec succès!'
            })
        except User.DoesNotExist:
            return JsonResponse({
                'success': False,
                'message': 'Utilisateur non trouvé.'
            })
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'Erreur lors de la modification de l\'utilisateur: {str(e)}'
            })
    return JsonResponse({
        'success': False,
        'message': 'Méthode non autorisée.'
    })

@csrf_exempt
def api_users_delete(request, user_id):
    """API pour supprimer un utilisateur"""
    if request.method == 'POST':
        try:
            user = User.objects.get(id=user_id)
            username = user.username  # Sauvegarder le nom pour le message
            
            # Vérifier si l'utilisateur a des emprunts actifs
            active_loans = Emprunt.objects.filter(lecteur=user, est_retourne=False).count()
            if active_loans > 0:
                return JsonResponse({
                    'success': False,
                    'message': f'Impossible de supprimer cet utilisateur car il a {active_loans} emprunt(s) actif(s).'
                })
            
            # Supprimer l'utilisateur
            user.delete()
            
            return JsonResponse({
                'success': True,
                'message': f'Utilisateur "{username}" supprimé avec succès!'
            })
        except User.DoesNotExist:
            return JsonResponse({
                'success': False,
                'message': 'Utilisateur non trouvé.'
            })
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'Erreur lors de la suppression de l\'utilisateur: {str(e)}'
            })
    return JsonResponse({
        'success': False,
        'message': 'Méthode non autorisée.'
    })

# API pour les réservations
@csrf_exempt
def api_reservations_validate(request, reservation_id):
    """API pour valider une réservation et la transformer en emprunt"""
    if request.method == 'POST':
        try:
            # Récupérer la réservation
            reservation = Reservation.objects.get(id=reservation_id)
            
            # Vérifier si la réservation est déjà validée
            if reservation.est_validee:
                return JsonResponse({
                    'success': False,
                    'message': 'Cette réservation a déjà été validée.'
                })
            
            # Vérifier si le livre est disponible
            if reservation.livre.stock <= 0:
                return JsonResponse({
                    'success': False,
                    'message': 'Le livre n\'est pas disponible en stock.'
                })
            
            # Vérifier si la réservation est payée
            if not reservation.est_payee:
                return JsonResponse({
                    'success': False,
                    'message': 'La réservation n\'a pas encore été payée.'
                })
            
            # Récupérer les données du formulaire
            date_emprunt_str = request.POST.get('date_emprunt')
            duree = int(request.POST.get('duree', 14))  # Durée par défaut: 14 jours
            
            # Convertir la date d'emprunt en objet date
            from datetime import datetime, timedelta
            date_emprunt = datetime.strptime(date_emprunt_str, '%Y-%m-%d').date()
            date_retour_prevue = date_emprunt + timedelta(days=duree)
            
            # Créer l'emprunt
            emprunt = Emprunt.objects.create(
                livre=reservation.livre,
                lecteur=reservation.lecteur,
                date_emprunt=date_emprunt,
                date_retour_prevue=date_retour_prevue,
                est_retourne=False
            )
            
            # Mettre à jour la réservation
            reservation.est_validee = True
            reservation.date_validation = datetime.now()
            reservation.save()
            
            # Mettre à jour le stock du livre
            reservation.livre.stock -= 1
            if reservation.livre.stock <= 0:
                reservation.livre.disponible = False
            reservation.livre.save()
            
            return JsonResponse({
                'success': True,
                'message': 'Réservation validée avec succès!',
                'emprunt_id': emprunt.id
            })
        except Reservation.DoesNotExist:
            return JsonResponse({
                'success': False,
                'message': 'Réservation non trouvée.'
            })
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'Erreur lors de la validation de la réservation: {str(e)}'
            })
    return JsonResponse({
        'success': False,
        'message': 'Méthode non autorisée.'
    })

@csrf_exempt
def valider_retour_livre(request):
    """Vue pour valider ou refuser une demande de retour de livre"""
    if request.method == 'POST':
        try:
            emprunt_id = request.POST.get('empruntId')
            action = request.POST.get('action')  # 'valider' ou 'refuser'

            if not emprunt_id or not action:
                return JsonResponse({
                    'success': False,
                    'message': 'Données manquantes.'
                })

            try:
                emprunt = Emprunt.objects.get(id=emprunt_id)

                if action == 'valider':
                    # Marquer l'emprunt comme retourné
                    emprunt.date_retour_reel = timezone.now()
                    emprunt.est_retourne = True
                    emprunt.save()

                    # Mettre à jour le stock du livre
                    livre = emprunt.livre
                    livre.stock += 1
                    if livre.stock > 0:
                        livre.disponible = True
                    livre.save()

                    return JsonResponse({
                        'success': True,
                        'message': 'Retour validé avec succès!'
                    })

                elif action == 'refuser':
                    # Simplement marquer la demande de retour comme refusée
                    # Dans un système réel, vous pourriez avoir un champ spécifique pour cela
                    emprunt.demande_retour = False
                    emprunt.save()

                    return JsonResponse({
                        'success': True,
                        'message': 'Demande de retour refusée.'
                    })

                return JsonResponse({
                    'success': False,
                    'message': 'Action non reconnue.'
                })

            except Emprunt.DoesNotExist:
                return JsonResponse({
                    'success': False,
                    'message': 'Emprunt non trouvé.'
                })

        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'Erreur: {str(e)}'
            })

    return JsonResponse({
        'success': False,
        'message': 'Méthode non autorisée.'
    })

# Vue pour retourner un livre emprunté
def return_book(request, emprunt_id):
    if request.method == 'POST':
        try:
            emprunt = get_object_or_404(Emprunt, id=emprunt_id)

            # Vérifier si l'utilisateur est autorisé
            if not request.user.is_staff:
                return JsonResponse({
                    'success': False,
                    'message': 'Vous n\'êtes pas autorisé à effectuer cette action.'
                })

            # Vérifier si une demande de retour existe
            retour = RetourLivre.objects.filter(emprunt=emprunt, statut='en_attente').first()

            if retour:
                # Valider la demande de retour
                retour.statut = 'valide'
                retour.date_validation = timezone.now()
                retour.save()

            # Mettre à jour le statut de l'emprunt
            emprunt.est_retourne = True
            emprunt.date_retour = timezone.now()
            emprunt.save()

            # Mettre à jour le stock du livre
            livre = emprunt.livre
            livre.stock += 1
            livre.save()

            # Envoyer un email de confirmation
            send_mail(
                'Retour de livre confirmé',
                f'Le retour du livre {livre.titre} a été confirmé.',
                'bibliotheque@example.com',
                [emprunt.lecteur.email],
                fail_silently=True,
            )

            # Traiter les réservations en attente
            process_reservations_for_book(livre)

            return JsonResponse({
                'success': True,
                'message': 'Livre retourné avec succès!'
            })

        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'Erreur lors du retour du livre: {str(e)}'
            })

    return JsonResponse({
        'success': False,
        'message': 'Méthode non autorisée.'
    })

@login_required
def request_return(request, emprunt_id):
    if request.method == 'POST':
        try:
            emprunt = get_object_or_404(Emprunt, id=emprunt_id)
            # Vérifier que l'emprunt appartient à l'utilisateur connecté
            if emprunt.lecteur == request.user:
                # Vérifier si une demande de retour existe déjà
                if RetourLivre.objects.filter(emprunt=emprunt, statut='en_attente').exists() or emprunt.demande_retour:
                    return JsonResponse({
                        'success': False,
                        'message': 'Une demande de retour existe déjà pour cet emprunt.'
                    })

                # Mettre à jour l'emprunt pour indiquer qu'une demande de retour a été faite
                now = timezone.now()
                emprunt.demande_retour = True
                emprunt.date_demande_retour = now
                emprunt.save()

                # Créer une demande de retour
                RetourLivre.objects.create(
                    emprunt=emprunt,
                    date_demande=now,
                    statut='en_attente'
                )
                
                # Afficher un message de succès
                messages.success(request, 'Votre demande de retour a été enregistrée et sera traitée par un administrateur.')
                
                # Si c'est une requête AJAX, retourner une réponse JSON
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({
                        'success': True,
                        'message': 'Demande de retour créée avec succès!'
                    })
                # Sinon, rediriger vers la page d'historique
                return redirect('history')
            else:
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({
                        'success': False,
                        'message': 'Accès non autorisé'
                    })
                messages.error(request, 'Vous n\'êtes pas autorisé à effectuer cette action.')
                return redirect('history')
        except Emprunt.DoesNotExist:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': False,
                    'message': 'Emprunt non trouvé'
                })
            messages.error(request, 'Emprunt non trouvé.')
            return redirect('history')
    # Si ce n'est pas une requête POST
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'success': False,
            'message': 'Méthode non autorisée.'
        })
    messages.error(request, 'Méthode non autorisée.')
    return redirect('history')

@staff_member_required
def validate_return(request, emprunt_id):
    """Valide le retour d'un livre emprunté."""
    # Accepter uniquement les requêtes POST pour la validation
    if request.method != 'POST':
        messages.error(request, 'Méthode non autorisée. Veuillez utiliser le formulaire de validation.')
        return redirect('dashboard_loans')
        
    try:
        # Récupérer l'emprunt
        emprunt = get_object_or_404(Emprunt, id=emprunt_id)
        
        # Vérifier si l'emprunt est déjà retourné
        if emprunt.est_retourne:
            messages.info(request, f'Le livre "{emprunt.livre.titre}" a déjà été retourné.')
            return redirect('dashboard_loans')
        
        # Mettre à jour l'emprunt
        now = timezone.now()
        emprunt.est_retourne = True
        emprunt.date_retour_reel = now.date()
        emprunt.demande_retour = False  # Réinitialiser car la demande a été traitée
        emprunt.retour_valide_admin = True  # Marquer que le retour a été validé par un administrateur
        emprunt.save()
        
        # Mettre à jour le statut de la demande de retour si elle existe
        retour = RetourLivre.objects.filter(emprunt=emprunt, statut='en_attente').first()
        if retour:
            retour.statut = 'valide'
            retour.date_validation = now
            retour.save()
        
        # Mettre à jour le stock du livre
        livre = emprunt.livre
        livre.stock += 1
        livre.disponible = True  # Assurer que le livre est marqué comme disponible
        livre.save()
        
        # Traiter les réservations en attente pour ce livre
        from .signals import process_reservations_for_book
        process_reservations_for_book(livre, 1)  # Traiter une unité nouvellement disponible
        
        # Envoyer un email de confirmation
        try:
            send_mail(
                'Retour de livre validé',
                f'Le retour du livre {livre.titre} a été validé.',
                'bibliotheque@example.com',
                [emprunt.lecteur.email],
                fail_silently=True,
            )
        except Exception as e:
            print(f"Erreur lors de l'envoi de l'email: {str(e)}")
        
        # Afficher un message de succès
        messages.success(request, f'Le retour du livre "{livre.titre}" a été validé avec succès.')
        
        # Rediriger vers la page principale du tableau de bord
        return redirect('dashboard')
        
    except Exception as e:
        print(f"Erreur lors de la validation du retour: {str(e)}")
        messages.error(request, f'Erreur lors de la validation du retour: {str(e)}')
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': False,
                'error': str(e)
            })
        
        return redirect('dashboard_loans')

@staff_member_required
def validate_return_ajax(request, emprunt_id):
    """Valide le retour d'un livre emprunté via AJAX sans redirection."""
    if request.method != 'POST':
        return JsonResponse({
            'success': False,
            'message': 'Méthode non autorisée.'
        })
    
    try:
        # Récupérer l'emprunt
        emprunt = get_object_or_404(Emprunt, id=emprunt_id)
        
        # Vérifier si l'emprunt est déjà retourné
        if emprunt.est_retourne:
            return JsonResponse({
                'success': False,
                'message': f'Le livre "{emprunt.livre.titre}" a déjà été retourné.'
            })
        
        # Mettre à jour l'emprunt
        now = timezone.now()
        emprunt.est_retourne = True
        emprunt.date_retour_reel = now.date()
        emprunt.demande_retour = False  # Réinitialiser car la demande a été traitée
        emprunt.retour_valide_admin = True  # Marquer que le retour a été validé par un administrateur
        emprunt.save()
        
        # Mettre à jour le statut de la demande de retour si elle existe
        retour = RetourLivre.objects.filter(emprunt=emprunt, statut='en_attente').first()
        if retour:
            retour.statut = 'valide'
            retour.date_validation = now
            retour.save()
        
        # Mettre à jour le stock du livre
        livre = emprunt.livre
        livre.stock += 1
        livre.disponible = True  # Assurer que le livre est marqué comme disponible
        livre.save()
        
        # Traiter les réservations en attente pour ce livre
        from .signals import process_reservations_for_book
        process_reservations_for_book(livre, 1)  # Traiter une unité nouvellement disponible
        
        return JsonResponse({
            'success': True,
            'message': 'Retour validé avec succès!',
            'emprunt_id': emprunt.id,
            'livre_titre': livre.titre,
            'date_retour': emprunt.date_retour_reel.strftime('%d/%m/%Y')
        })
    
    except Exception as e:
        print(f"Erreur lors de la validation du retour via AJAX: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        })

@staff_member_required
def refuse_return_simple(request, emprunt_id):
    """Refuse automatiquement la demande de retour d'un livre emprunté sans nécessiter de cocher une case."""
    # Accepter uniquement les requêtes POST pour le refus
    if request.method != 'POST':
        messages.error(request, 'Méthode non autorisée. Veuillez utiliser le formulaire de refus.')
        return redirect('dashboard_loans')
        
    try:
        # Récupérer l'emprunt
        emprunt = get_object_or_404(Emprunt, id=emprunt_id)
        
        # Vérifier si l'emprunt est déjà retourné
        if emprunt.est_retourne:
            messages.info(request, f'Le livre "{emprunt.livre.titre}" a déjà été retourné.')
            return redirect('dashboard')
        
        # Vérifier s'il y a une demande de retour
        if not emprunt.demande_retour:
            messages.warning(request, f'Aucune demande de retour en attente pour le livre "{emprunt.livre.titre}".')
            return redirect('dashboard')
        
        # Mettre à jour le statut de la demande de retour si elle existe
        retour = RetourLivre.objects.filter(emprunt=emprunt, statut='en_attente').first()
        if retour:
            retour.statut = 'refuse'
            retour.date_validation = timezone.now()
            retour.save()
        
        # Réinitialiser la demande de retour sur l'emprunt
        emprunt.demande_retour = False
        emprunt.date_demande_retour = None
        emprunt.save()
        
        # Créer une notification pour l'utilisateur si la classe existe
        try:
            from .models import Notification
            Notification.objects.create(
                user=emprunt.lecteur,
                title='Demande de retour refusée',
                message=f'Votre demande de retour pour le livre {emprunt.livre.titre} a été refusée.',
                notification_type='retour',
                link=reverse('book_details', args=[emprunt.livre.id])
            )
        except (ImportError, AttributeError):
            # Si la classe Notification n'existe pas, ignorer cette partie
            pass
        
        # Afficher un message de succès
        messages.success(request, f'La demande de retour pour le livre "{emprunt.livre.titre}" a été refusée.')
        
        # Rediriger vers la page principale du tableau de bord
        return redirect('dashboard')
        
    except Exception as e:
        print(f"Erreur lors du refus de la demande de retour: {str(e)}")
        messages.error(request, f'Erreur lors du refus de la demande de retour: {str(e)}')
        return redirect('dashboard')

@staff_member_required
def refuse_return(request, emprunt_id):
    """Refuse la demande de retour d'un livre emprunté."""
    # Accepter uniquement les requêtes POST pour le refus
    if request.method != 'POST':
        messages.error(request, 'Méthode non autorisée. Veuillez utiliser le formulaire de refus.')
        return redirect('dashboard_loans')
        
    try:
        # Récupérer l'emprunt
        emprunt = get_object_or_404(Emprunt, id=emprunt_id)
        
        # Vérifier si l'emprunt est déjà retourné
        if emprunt.est_retourne:
            messages.info(request, f'Le livre "{emprunt.livre.titre}" a déjà été retourné.')
            return redirect('dashboard_loans')
        
        # Vérifier s'il y a une demande de retour
        if not emprunt.demande_retour:
            messages.warning(request, f'Aucune demande de retour en attente pour le livre "{emprunt.livre.titre}".')
            return redirect('dashboard_loans')
        
        # Mettre à jour le statut de la demande de retour si elle existe
        retour = RetourLivre.objects.filter(emprunt=emprunt, statut='en_attente').first()
        if retour:
            retour.statut = 'refuse'
            retour.date_validation = timezone.now()
            retour.save()
        
        # Réinitialiser la demande de retour sur l'emprunt
        emprunt.demande_retour = False
        emprunt.date_demande_retour = None
        emprunt.save()
        
        # Créer une notification pour l'utilisateur si la classe existe
        try:
            from .models import Notification
            Notification.objects.create(
                user=emprunt.lecteur,
                title='Demande de retour refusée',
                message=f'Votre demande de retour pour le livre {emprunt.livre.titre} a été refusée.',
                notification_type='retour',
                link=reverse('book_details', args=[emprunt.livre.id])
            )
        except (ImportError, AttributeError):
            # Si la classe Notification n'existe pas, ignorer cette partie
            pass
        
        # Afficher un message de succès
        messages.success(request, f'La demande de retour pour le livre "{emprunt.livre.titre}" a été refusée.')
        
        # Répondre en fonction du type de requête
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                'message': 'Demande de retour refusée avec succès!'
            })
        
        # Rediriger vers la page principale du tableau de bord
        return redirect('dashboard')
        
    except Exception as e:
        print(f"Erreur lors du refus de la demande de retour: {str(e)}")
        messages.error(request, f'Erreur lors du refus de la demande de retour: {str(e)}')
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': False,
                'error': str(e)
            })
        
        return redirect('dashboard_loans')

@staff_member_required
def valider_retour(request, emprunt_id):
    """Validation du retour d'un emprunt par un superuser/admin."""
    emprunt = get_object_or_404(Emprunt, id=emprunt_id, retour_demande=True, retour_valide=False)
    if request.method == 'POST':
        from .models import Amende
        emprunt.date_retour_effective = timezone.now().date()
        emprunt.retour_valide = True
        emprunt.save()
        # Ne pas augmenter manuellement le stock ici, la fonction rendre() s'en chargera
        # VÃ©rifier s'il y a un retard
        if emprunt.date_retour_effective > emprunt.date_retour_prevue:
            jours_retard = (emprunt.date_retour_effective - emprunt.date_retour_prevue).days
            montant = 10 * jours_retard
            Amende.objects.create(
                emprunt=emprunt,
                lecteur=emprunt.lecteur,
                montant=montant,
                raison=f"Retard de {jours_retard} jour(s)",
                payee=False
            )
            messages.warning(request, f"Retour validÃ© avec {jours_retard} jour(s) de retard. Amende de {montant} DH gÃ©nÃ©rÃ©e.")
        else:
            messages.success(request, f"Retour du livre '{emprunt.livre.titre}' validÃ©.")
        
        # Augmenter le stock pour dÃ©clencher le signal qui traitera les rÃ©servations
        livre = emprunt.livre
        livre.stock += 1
        livre.save()
    return redirect('history')

@login_required
def annuler_reservation(request, reservation_id):
    """Annule une rÃ©servation."""
    reservation = get_object_or_404(Reservation, id=reservation_id, lecteur=request.user)
    if request.method == 'POST':
        print('MÃ©thode POST dÃ©tectÃ©e')  # DEBUG
        reservation.delete()
        messages.success(request, f"La rÃ©servation du livre '{reservation.livre.titre}' a Ã©tÃ© annulÃ©e.")
    return redirect('history')
# La vue reservation_options a Ã©tÃ© supprimÃ©e car elle n'est plus nÃ©cessaire.
# Les options de rÃ©servation sont maintenant gÃ©rÃ©es directement dans la page de dÃ©tails du livre.

@login_required
def payer_reservation(request, reservation_id):
    from .models import Amende, Livre
    # VÃ©rifier si l'utilisateur a des amendes non rÃ©glÃ©es
    has_amendes, amendes_non_payees = check_amende(request)
    
    # Si l'utilisateur a des amendes, bloquer l'accÃ¨s et rediriger vers l'historique
    if has_amendes:
        # Forcer l'affichage du popup d'amende
        request.session['force_amende_popup'] = True
        request.session['action_tentee'] = 'payer_reservation'
        
        # Identifier le livre ou la rÃ©servation concernÃ©e
        try:
            # Essayer de convertir en entier pour dÃ©terminer si c'est un ID valide
            reservation_id_int = int(reservation_id)
            
            # VÃ©rifier si c'est un ID de livre plutÃ´t qu'un ID de rÃ©servation
            if Livre.objects.filter(id=reservation_id_int).exists():
                livre = get_object_or_404(Livre, id=reservation_id_int)
                # Rediriger vers la page de dÃ©tails du livre
                messages.error(request, "Vous avez des amendes non payÃ©es. Veuillez les rÃ©gler avant de pouvoir effectuer un paiement.")
                return redirect('book_details', livre_id=livre.id)
            else:
                reservation = get_object_or_404(Reservation, id=reservation_id_int, lecteur=request.user)
                livre = reservation.livre
                # Rediriger vers la page de dÃ©tails du livre
                messages.error(request, "Vous avez des amendes non payÃ©es. Veuillez les rÃ©gler avant de pouvoir payer votre rÃ©servation.")
                return redirect('book_details', livre_id=livre.id)
        except (ValueError, TypeError):
            messages.error(request, "ID de rÃ©servation ou de livre invalide et vous avez des amendes non payÃ©es.")
            return redirect('history')
    
    # VÃ©rifier si on a un ID de rÃ©servation ou un ID de livre
    try:
        # Essayer de convertir en entier pour dÃ©terminer si c'est un ID valide
        reservation_id = int(reservation_id)
        
        # VÃ©rifier si c'est un ID de livre plutÃ´t qu'un ID de rÃ©servation
        if Livre.objects.filter(id=reservation_id).exists():
            # C'est un ID de livre, rÃ©cupÃ©rer le livre mais ne pas crÃ©er de rÃ©servation tout de suite
            livre = get_object_or_404(Livre, id=reservation_id)
            
            # VÃ©rifier si l'utilisateur a dÃ©jÃ  rÃ©servÃ© ce livre
            if Reservation.objects.filter(livre=livre, lecteur=request.user).exists():
                messages.info(request, "Vous avez dÃ©jÃ  rÃ©servÃ© ce livre.")
                return redirect('book_details', livre_id=livre.id)
                
            # VÃ©rifier si l'utilisateur a dÃ©jÃ  empruntÃ© ce livre et ne l'a pas encore rendu
            emprunt_en_cours = Emprunt.objects.filter(
                livre=livre, 
                lecteur=request.user, 
                date_retour_reel__isnull=True
            ).exists()
            
            if emprunt_en_cours:
                messages.error(request, "Vous ne pouvez pas rÃ©server ce livre car vous l'avez dÃ©jÃ  empruntÃ©.")
                return redirect('book_details', livre_id=livre.id)
                
            # On ne crÃ©e pas encore la rÃ©servation, on la crÃ©era aprÃ¨s le paiement
            reservation = None
        else:
            # C'est un ID de rÃ©servation, rÃ©cupÃ©rer la rÃ©servation existante
            reservation = get_object_or_404(Reservation, id=reservation_id, lecteur=request.user)
            livre = reservation.livre
            
            # VÃ©rifier si l'utilisateur a dÃ©jÃ  empruntÃ© ce livre et ne l'a pas encore rendu
            emprunt_en_cours = Emprunt.objects.filter(
                livre=livre, 
                lecteur=request.user, 
                date_retour_reel__isnull=True
            ).exists()
            
            if emprunt_en_cours:
                # Supprimer la rÃ©servation car elle n'est plus nÃ©cessaire
                reservation.delete()
                messages.error(request, "Vous ne pouvez pas rÃ©server ce livre car vous l'avez dÃ©jÃ  empruntÃ©. Votre rÃ©servation a Ã©tÃ© annulÃ©e.")
                return redirect('book_details', livre_id=livre.id)
    except (ValueError, Reservation.DoesNotExist):
        messages.error(request, "La rÃ©servation que vous essayez de payer n'existe pas ou a Ã©tÃ© annulÃ©e.")
        return redirect('home')
    
    if request.method == 'POST':
        # VÃ©rifier que tous les champs du formulaire sont remplis
        cardholder = request.POST.get('cardholder')
        cardnumber = request.POST.get('cardnumber')
        expdate = request.POST.get('expdate')
        cvv = request.POST.get('cvv')
        
        if not all([cardholder, cardnumber, expdate, cvv]):
            messages.error(request, "Veuillez remplir tous les champs du formulaire de paiement.")
            return render(request, 'library/payer_reservation.html', {'reservation': reservation, 'livre': livre})
        
        # VÃ©rification de base du format des donnÃ©es de carte
        import re
        if not re.match(r'^[0-9 ]{13,19}$', cardnumber):
            messages.error(request, "Le numÃ©ro de carte n'est pas valide.")
            return render(request, 'library/payer_reservation.html', {'reservation': reservation, 'livre': livre})
        
        if not re.match(r'^(0[1-9]|1[0-2])\/\d{2}$', expdate):
            messages.error(request, "La date d'expiration n'est pas valide. Utilisez le format MM/AA.")
            return render(request, 'library/payer_reservation.html', {'reservation': reservation, 'livre': livre})
        
        if not re.match(r'^\d{3,4}$', cvv):
            messages.error(request, "Le code CVV n'est pas valide.")
            return render(request, 'library/payer_reservation.html', {'reservation': reservation, 'livre': livre})
        
        # Paiement accepté
        from django.utils import timezone
        from datetime import timedelta
        from .models import Payment
        
        # Vérifier le stock du livre
        stock_disponible = livre.stock > 0
        
        # Si c'est un ID de livre (pas de réservation existante), créer la réservation ou l'emprunt maintenant
        if reservation is None:
            if stock_disponible:
                # Si le stock est disponible, créer directement un emprunt
                emprunt = Emprunt.objects.create(
                    livre=livre,
                    lecteur=request.user,
                    date_emprunt=timezone.now(),
                    date_retour_prevue=timezone.now() + timedelta(days=7),
                    retour_valide_admin=False  # Pas encore retourné
                )
                
                # Mettre à jour le stock du livre
                livre.stock -= 1
                if livre.stock <= 0:
                    livre.disponible = False
                livre.save()
                
                # Créer un paiement pour l'emprunt
                payment = Payment.objects.create(
                    user=request.user, 
                    livre=livre, 
                    emprunt=emprunt,
                    amount=livre.prix, 
                    is_valid=True,
                    description=f"Emprunt du livre '{livre.titre}'"
                )
                
                messages.success(request, f"Emprunt créé avec succès ! Vous devez retourner le livre avant le {emprunt.date_retour_prevue.strftime('%d/%m/%Y')}.")
            else:
                # Si le stock n'est pas disponible, créer une réservation
                reservation = Reservation.objects.create(
                    livre=livre,
                    lecteur=request.user,
                    est_payee=True  # Déjà marquée comme payée puisque le paiement est validé
                )
                
                payment = Payment.objects.create(
                    user=request.user, 
                    livre=livre, 
                    reservation=reservation, 
                    amount=livre.prix, 
                    is_valid=True,
                    description=f"Réservation du livre '{livre.titre}'"
                )
                
                messages.success(request, "Réservation créée et payée avec succès ! Vous serez notifié dès que le livre sera disponible.")
        else:
            # C'est une réservation existante
            if stock_disponible:
                # Si le stock est disponible, convertir la réservation en emprunt
                emprunt = Emprunt.objects.create(
                    livre=livre,
                    lecteur=request.user,
                    date_emprunt=timezone.now(),
                    date_retour_prevue=timezone.now() + timedelta(days=7),
                    retour_valide_admin=False  # Pas encore retourné
                )
                
                # Mettre à jour le stock du livre
                livre.stock -= 1
                if livre.stock <= 0:
                    livre.disponible = False
                livre.save()
                
                # Créer un paiement pour l'emprunt
                payment = Payment.objects.create(
                    user=request.user, 
                    livre=livre, 
                    emprunt=emprunt,
                    amount=livre.prix, 
                    is_valid=True,
                    description=f"Conversion de réservation en emprunt pour '{livre.titre}'"
                )
                
                # Supprimer la réservation car elle est maintenant convertie en emprunt
                reservation.delete()
                
                messages.success(request, f"Votre réservation a été convertie en emprunt ! Vous devez retourner le livre avant le {emprunt.date_retour_prevue.strftime('%d/%m/%Y')}.")
            else:
                # Même si le stock n'est pas disponible, créer un emprunt automatiquement avec un délai de 7 jours
                emprunt = Emprunt.objects.create(
                    livre=livre,
                    lecteur=request.user,
                    date_emprunt=timezone.now(),
                    date_retour_prevue=timezone.now() + timedelta(days=7),
                    retour_valide_admin=False  # Pas encore retourné
                )
                
                # D'abord, marquer la réservation comme payée
                reservation.est_payee = True
                reservation.save()
                
                # Ensuite, créer un paiement lié uniquement à l'emprunt
                payment = Payment.objects.create(
                    user=request.user, 
                    livre=livre, 
                    emprunt=emprunt,
                    amount=livre.prix, 
                    is_valid=True,
                    description=f"Conversion de réservation en emprunt pour '{livre.titre}'"
                )
                
                # Créer une notification pour l'utilisateur si la classe existe
                try:
                    from .models import Notification
                    Notification.objects.create(
                        user=request.user,
                        title='Livre emprunté',
                        message=f"Le livre {livre.titre} a été automatiquement ajouté à vos emprunts. Vous devez le retourner avant le {emprunt.date_retour_prevue.strftime('%d/%m/%Y')}.",
                        notification_type='emprunt',
                        link=reverse('book_details', args=[livre.id])
                    )
                except (ImportError, AttributeError):
                    # Si la classe Notification n'existe pas, ignorer cette partie
                    pass
                
                # Envoyer un email pour informer l'utilisateur
                try:
                    from django.core.mail import send_mail
                    from django.conf import settings
                    
                    send_mail(
                        'Votre livre réservé est maintenant emprunté',
                        f'Bonjour {request.user.username},\n\n'
                        f'Le livre "{livre.titre}" que vous avez réservé et payé a été automatiquement ajouté à vos emprunts. '
                        f'Vous devez le retourner avant le {emprunt.date_retour_prevue.strftime("%d/%m/%Y")}.\n\n'
                        f'Cordialement,\nL\'\u00e9quipe BiblioSmart',
                        settings.DEFAULT_FROM_EMAIL if hasattr(settings, 'DEFAULT_FROM_EMAIL') else 'bibliotheque@example.com',
                        [request.user.email],
                        fail_silently=True,
                    )
                    print(f"Email envoyé à {request.user.email}")
                except Exception as e:
                    print(f"Erreur lors de l'envoi de l'email: {str(e)}")  # Log l'erreur pour débogage
                
                # Supprimer la réservation car elle est maintenant convertie en emprunt
                reservation_id = reservation.id
                reservation.delete()
                print(f"Réservation {reservation_id} supprimée après conversion en emprunt")
                
                messages.success(request, f"Paiement de réservation effectué avec succès ! Le livre a été automatiquement ajouté à vos emprunts. Vous devez le retourner avant le {emprunt.date_retour_prevue.strftime('%d/%m/%Y')}.")
                
                # Mettre à jour le stock du livre si nécessaire
                if livre.stock > 0:
                    livre.stock -= 1
                    if livre.stock <= 0:
                        livre.disponible = False
                    livre.save()
            
        # Rediriger vers la page de détails du livre
        return redirect('book_details', livre_id=livre.id)
    return render(request, 'library/payer_reservation.html', {'reservation': reservation, 'livre': livre})

@login_required
def payer_emprunt(request, reservation_id):
    """Permet de payer un emprunt directement depuis une notification."""
    from .models import Amende, Livre, Reservation
    # Vérifier si l'utilisateur a des amendes non réglées
    has_amendes, amendes_non_payees = check_amende(request)
    
    # Si l'utilisateur a des amendes, bloquer l'accès et rediriger vers l'historique
    if has_amendes:
        # Forcer l'affichage du popup d'amende
        request.session['force_amende_popup'] = True
        request.session['action_tentee'] = 'payer_emprunt'
        
        try:
            reservation = get_object_or_404(Reservation, id=reservation_id, lecteur=request.user)
            livre = reservation.livre
            # Rediriger vers la page de détails du livre
            messages.error(request, "Vous avez des amendes non payées. Veuillez les régler avant de pouvoir payer votre emprunt.")
            return redirect('book_details', livre_id=livre.id)
        except (ValueError, TypeError, Reservation.DoesNotExist):
            messages.error(request, "ID de réservation invalide et vous avez des amendes non payées.")
            return redirect('history')
    
    try:
        # Récupérer la réservation existante
        reservation = get_object_or_404(Reservation, id=reservation_id, lecteur=request.user)
        livre = reservation.livre
        
        # Vérifier si l'utilisateur a déjà emprunté ce livre et ne l'a pas encore rendu
        emprunt_en_cours = Emprunt.objects.filter(
            livre=livre, 
            lecteur=request.user, 
            date_retour_reel__isnull=True
        ).exists()
        
        if emprunt_en_cours:
            # Supprimer la réservation car elle n'est plus nécessaire
            reservation.delete()
            messages.error(request, "Vous ne pouvez pas réserver ce livre car vous l'avez déjà emprunté. Votre réservation a été annulée.")
            return redirect('book_details', livre_id=livre.id)
    except (ValueError, Reservation.DoesNotExist):
        messages.error(request, "La réservation que vous essayez de payer n'existe pas ou a été annulée.")
        return redirect('home')
    
    # Vérifier si la réservation est déjà payée
    if reservation.est_payee:
        # Si la réservation est déjà payée, créer directement un emprunt sans demander de paiement
        from django.utils import timezone
        from datetime import timedelta
        from .models import Payment
        
        # Créer un emprunt automatiquement avec un délai de 7 jours
        emprunt = Emprunt.objects.create(
            livre=livre,
            lecteur=request.user,
            date_emprunt=timezone.now(),
            date_retour_prevue=timezone.now() + timedelta(days=7),
            retour_valide_admin=False  # Pas encore retourné
        )
        
        # Mettre à jour le stock du livre si nécessaire
        if livre.stock > 0:
            livre.stock -= 1
            if livre.stock <= 0:
                livre.disponible = False
            livre.save()
        
        # Créer une notification pour l'utilisateur si la classe existe
        try:
            from .models import Notification
            Notification.objects.create(
                user=request.user,
                title='Livre emprunté',
                message=f"Le livre {livre.titre} a été automatiquement ajouté à vos emprunts. Vous devez le retourner avant le {emprunt.date_retour_prevue.strftime('%d/%m/%Y')}.",
                notification_type='emprunt',
                link=reverse('book_details', args=[livre.id])
            )
        except (ImportError, AttributeError):
            # Si la classe Notification n'existe pas, ignorer cette partie
            pass
            
        # Envoyer un email pour informer l'utilisateur
        try:
            from django.core.mail import send_mail
            from django.conf import settings
            
            send_mail(
                'Votre réservation a été convertie en emprunt',
                f'Bonjour {request.user.username},\n\n'
                f'Votre réservation pour le livre "{livre.titre}" a été convertie en emprunt. '
                f'Vous n\'avez pas eu besoin de payer à nouveau car vous aviez déjà payé lors de la réservation.\n\n'
                f'Vous devez retourner le livre avant le {emprunt.date_retour_prevue.strftime("%d/%m/%Y")}.\n\n'
                f'Cordialement,\nL\'\u00e9quipe BiblioSmart',
                settings.DEFAULT_FROM_EMAIL if hasattr(settings, 'DEFAULT_FROM_EMAIL') else 'bibliotheque@example.com',
                [request.user.email],
                fail_silently=True,
            )
            print(f"Email envoyé à {request.user.email}")
        except Exception as e:
            print(f"Erreur lors de l'envoi de l'email: {str(e)}")  # Log l'erreur pour débogage
        
        # Supprimer la réservation car elle est maintenant convertie en emprunt
        reservation.delete()
        
        messages.success(request, f"Votre réservation a été convertie en emprunt ! Vous n'avez pas besoin de payer à nouveau car vous avez déjà payé lors de la réservation. Vous devez retourner le livre avant le {emprunt.date_retour_prevue.strftime('%d/%m/%Y')}.")
        
        # Rediriger vers la page de détails du livre
        return redirect('book_details', livre_id=livre.id)
    
    if request.method == 'POST':
        # Vérifier que tous les champs du formulaire sont remplis
        cardholder = request.POST.get('cardholder')
        cardnumber = request.POST.get('cardnumber')
        expdate = request.POST.get('expdate')
        cvv = request.POST.get('cvv')
        
        if not all([cardholder, cardnumber, expdate, cvv]):
            messages.error(request, "Veuillez remplir tous les champs du formulaire de paiement.")
            return render(request, 'library/payer_emprunt.html', {'reservation': reservation, 'livre': livre})
        
        # Vérification de base du format des données de carte
        import re
        if not re.match(r'^[0-9 ]{13,19}$', cardnumber):
            messages.error(request, "Le numéro de carte n'est pas valide.")
            return render(request, 'library/payer_emprunt.html', {'reservation': reservation, 'livre': livre})
        
        if not re.match(r'^(0[1-9]|1[0-2])\/\d{2}$', expdate):
            messages.error(request, "La date d'expiration n'est pas valide. Utilisez le format MM/AA.")
            return render(request, 'library/payer_emprunt.html', {'reservation': reservation, 'livre': livre})
        
        if not re.match(r'^\d{3,4}$', cvv):
            messages.error(request, "Le code CVV n'est pas valide.")
            return render(request, 'library/payer_emprunt.html', {'reservation': reservation, 'livre': livre})
        
        # Paiement accepté
        from django.utils import timezone
        from datetime import timedelta
        from .models import Payment
        
        # Vérifier le stock du livre
        stock_disponible = livre.stock > 0
        
        if stock_disponible:
            # Si le stock est disponible, convertir la réservation en emprunt
            emprunt = Emprunt.objects.create(
                livre=livre,
                lecteur=request.user,
                date_emprunt=timezone.now(),
                date_retour_prevue=timezone.now() + timedelta(days=7),
                retour_valide_admin=False  # Pas encore retourné
            )
            
            # Mettre à jour le stock du livre
            livre.stock -= 1
            if livre.stock <= 0:
                livre.disponible = False
            livre.save()
            
            # Créer un paiement pour l'emprunt
            payment = Payment.objects.create(
                user=request.user, 
                livre=livre, 
                emprunt=emprunt,
                reservation=reservation,
                amount=livre.prix, 
                is_valid=True,
                description=f"Conversion de réservation en emprunt pour '{livre.titre}'"
            )
            
            # Supprimer la réservation car elle est maintenant convertie en emprunt
            reservation.delete()
            
            messages.success(request, f"Votre réservation a été convertie en emprunt ! Vous devez retourner le livre avant le {emprunt.date_retour_prevue.strftime('%d/%m/%Y')}.")
        else:
            # Si le stock n'est pas disponible, marquer simplement la réservation comme payée
            payment = Payment.objects.create(
                user=request.user, 
                livre=livre, 
                reservation=reservation, 
                amount=livre.prix, 
                is_valid=True,
                description=f"Paiement d'emprunt pour '{livre.titre}'"
            )
            
            reservation.est_payee = True
            reservation.save()
            
            messages.success(request, "Paiement d'emprunt effectué avec succès ! Vous serez notifié dès que le livre sera disponible.")
        
        # Rediriger vers la page de détails du livre
        return redirect('book_details', livre_id=livre.id)
    
    return render(request, 'library/payer_emprunt.html', {'reservation': reservation, 'livre': livre})

@login_required
def clear_amende_session(request):
    """Efface les variables de session liées aux amendes."""
    if request.method == 'POST':
        if 'force_amende_popup' in request.session:
            del request.session['force_amende_popup']
        if 'action_tentee' in request.session:
            del request.session['action_tentee']
        request.session.modified = True
    return redirect(request.META.get('HTTP_REFERER', 'home'))
@staff_member_required
def gerer_utilisateur(request):
    """Vue pour ajouter, modifier, récupérer ou supprimer un utilisateur"""
    # GET pour récupérer les détails d'un utilisateur
    if request.method == 'GET':
        user_id = request.GET.get('user_id')
        if user_id:
            try:
                user = User.objects.get(id=user_id)
                return JsonResponse({
                    'success': True,
                    'user': {
                        'id': user.id,
                        'username': user.username,
                        'email': user.email,
                        'is_superuser': user.is_superuser,
                        'date_joined': user.date_joined.strftime('%Y-%m-%d')
                    }
                })
            except User.DoesNotExist:
                return JsonResponse({
                    'success': False,
                    'message': 'Utilisateur non trouvé.'
                })
            except Exception as e:
                return JsonResponse({
                    'success': False,
                    'message': f'Erreur: {str(e)}'
                })
        return JsonResponse({
            'success': False,
            'message': 'ID utilisateur non fourni.'
        })
    
    # POST pour ajouter, modifier ou supprimer un utilisateur
    elif request.method == 'POST':
        try:
            user_id = request.POST.get('userId', '')
            action = request.POST.get('action', '')
            
            # Gestion de la suppression
            if action == 'delete' and user_id:
                try:
                    user = User.objects.get(id=user_id)
                    username = user.username  # Sauvegarder le nom pour le message
                    user.delete()
                    return JsonResponse({
                        'success': True,
                        'message': f'Utilisateur "{username}" supprimé avec succès!'
                    })
                except User.DoesNotExist:
                    return JsonResponse({
                        'success': False,
                        'message': 'Utilisateur non trouvé.'
                    })
                except Exception as e:
                    return JsonResponse({
                        'success': False,
                        'message': f'Erreur lors de la suppression: {str(e)}'
                    })
            
            # Récupérer les données du formulaire
            username = request.POST.get('username', '')
            email = request.POST.get('email', '')
            password = request.POST.get('password', '')
            is_superuser = request.POST.get('is_superuser') == '1'
            
            # Ajout d'un nouvel utilisateur
            if not user_id:
                # Vérifier si le nom d'utilisateur existe déjà 
                if User.objects.filter(username=username).exists():
                    return JsonResponse({
                        'success': False,
                        'message': 'Ce nom d\'utilisateur existe déjà.'
                    })
                
                # Vérifier si l'email existe déjà 
                if User.objects.filter(email=email).exists():
                    return JsonResponse({
                        'success': False,
                        'message': 'Cette adresse email est déjà utilisée.'
                    })
                
                # Créer un nouvel utilisateur
                user = User.objects.create_user(
                    username=username,
                    email=email,
                    password=password if password else None
                )
                
                # Définir les droits d'administrateur si nécessaire
                if is_superuser:
                    user.is_superuser = True
                    user.is_staff = True
                    user.save()
                
                return JsonResponse({
                    'success': True,
                    'message': 'Utilisateur ajouté avec succès!',
                    'user_id': user.id
                })
            
            # Modification d'un utilisateur existant
            else:
                try:
                    user = User.objects.get(id=user_id)
                    
                    # Vérifier si le nom d'utilisateur existe déjà (sauf pour l'utilisateur actuel)
                    if username and username != user.username:
                        if User.objects.filter(username=username).exists():
                            return JsonResponse({
                                'success': False,
                                'message': 'Ce nom d\'utilisateur existe déjà.'
                            })
                        user.username = username
                    
                    # Vérifier si l'email existe déjà (sauf pour l'utilisateur actuel)
                    if email and email != user.email:
                        if User.objects.filter(email=email).exists():
                            return JsonResponse({
                                'success': False,
                                'message': 'Cette adresse email est déjà utilisée.'
                            })
                        user.email = email
                    
                    # Mettre à jour le mot de passe si fourni
                    if password:
                        user.set_password(password)
                    
                    # Mettre à jour les droits d'administrateur
                    user.is_superuser = is_superuser
                    user.is_staff = is_superuser
                    
                    user.save()
                    
                    return JsonResponse({
                        'success': True,
                        'message': 'Utilisateur modifié avec succès!'
                    })
                    
                except User.DoesNotExist:
                    return JsonResponse({
                        'success': False,
                        'message': 'Utilisateur non trouvé.'
                    })
            
            return JsonResponse({
                'success': False,
                'message': 'Action non reconnue.'
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'Erreur: {str(e)}'
            })
    
    # Si la méthode n'est pas GET ou POST
    return JsonResponse({
        'success': False,
        'message': 'Méthode non autorisée.'
    })


@staff_member_required
def validate_return(request, emprunt_id):
    if request.method == 'POST':
        try:
            emprunt = get_object_or_404(Emprunt, id=emprunt_id)
            retour = RetourLivre.objects.filter(emprunt=emprunt, statut='en_attente').first()
            
            if not retour and not emprunt.demande_retour:
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({
                        'success': False,
                        'error': 'Aucune demande de retour en attente pour cet emprunt.'
                    })
                messages.error(request, 'Aucune demande de retour en attente pour cet emprunt.')
                return redirect('dashboard_loans')
            
            now = timezone.now()
            
            # Mettre à jour le statut de la demande de retour si elle existe
            if retour:
                retour.statut = 'refuse'
                retour.date_validation = now
                retour.save()
            
            # Mettre à jour l'emprunt pour indiquer que la demande a été refusée
            emprunt.demande_retour = False  # Réinitialiser car la demande a été traitée (refusée)
            emprunt.save()
            
            # Envoyer un email de notification de refus
            try:
                send_mail(
                    'Demande de retour refusée',
                    f'Votre demande de retour pour le livre "{emprunt.livre.titre}" a été refusée. ' +
                    'Veuillez contacter la bibliothèque pour plus d\'informations.',
                    'bibliotheque@example.com',
                    [emprunt.lecteur.email],
                    fail_silently=True,
                )
            except Exception as e:
                print(f"Erreur lors de l'envoi de l'email: {str(e)}")
            
            # Afficher un message de succès pour l'administrateur
            messages.success(request, f'La demande de retour pour le livre "{emprunt.livre.titre}" a été refusée.')
            
            # Répondre en fonction du type de requête
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': True,
                    'message': 'Demande de retour refusée avec succès!'
                })
            return redirect('dashboard_loans')
            
        except Exception as e:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': False,
                    'error': str(e)
                })
            messages.error(request, f'Erreur lors du refus de la demande de retour: {str(e)}')
            return redirect('dashboard_loans')

    
    return JsonResponse({
        'success': False,
        'error': 'Méthode non autorisée'
    })


@staff_member_required
def refuse_return(request, emprunt_id):
    """Vue pour refuser une demande de retour de livre"""
    if request.method == 'POST':
        try:
            emprunt = get_object_or_404(Emprunt, id=emprunt_id)
            retour = RetourLivre.objects.filter(emprunt=emprunt, statut='en_attente').first()
            
            if not retour:
                return JsonResponse({
                    'success': False,
                    'error': 'Aucune demande de retour en attente pour cet emprunt.'
                })
            
            # Mettre à jour le statut de la demande de retour
            retour.statut = 'refuse'
            retour.date_validation = timezone.now()
            retour.save()
            
            # Envoyer un email d'information
            send_mail(
                'Demande de retour refusée',
                f'Votre demande de retour pour le livre {emprunt.livre.titre} a été refusée.',
                'bibliotheque@example.com',
                [emprunt.lecteur.email],
                fail_silently=True,
            )
            
            return JsonResponse({
                'success': True
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            })
    
    return JsonResponse({
        'success': False,
        'error': 'Méthode non autorisée'
    })