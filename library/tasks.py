from django.utils import timezone
from datetime import timedelta
from .models import Reservation, Emprunt
from django.core.mail import send_mail
from django.conf import settings

def process_reservations():
    """
    Tâche planifiée pour traiter les réservations après 24h de disponibilité.
    
    Cette fonction:
    1. Crée automatiquement les emprunts pour les réservations payées après 24h
    2. Annule les réservations non payées après 24h et passe au lecteur suivant
    """
    now = timezone.now()
    cutoff_time = now - timedelta(hours=24)
    
    # Traiter les réservations payées disponibles depuis plus de 24h
    reservations_payees = Reservation.objects.filter(
        est_payee=True,
        date_disponibilite__lt=cutoff_time
    )
    
    for reservation in reservations_payees:
        # Créer un emprunt pour cette réservation
        emprunt = Emprunt.objects.create(
            livre=reservation.livre,
            lecteur=reservation.lecteur,
            date_retour_prevue=timezone.now().date() + timedelta(days=7)
        )
        
        # Envoyer un email pour informer l'utilisateur
        try:
            send_mail(
                'Votre emprunt a été automatiquement créé',
                f'Bonjour {reservation.lecteur.username},\n\n'
                f'Le livre "{reservation.livre.titre}" que vous avez réservé et payé est maintenant emprunté à votre nom. '
                f'Vous pouvez venir le récupérer à la bibliothèque.\n\n'
                f'Date de retour prévue : {emprunt.date_retour_prevue.strftime("%d/%m/%Y")}\n\n'
                f'Cordialement,\nL\'équipe BiblioSmart',
                settings.DEFAULT_FROM_EMAIL,
                [reservation.lecteur.email],
                fail_silently=True,
            )
        except Exception:
            pass  # Gérer silencieusement les erreurs d'envoi d'email
        
        # Supprimer la réservation
        reservation.delete()
    
    # Traiter les réservations non payées disponibles depuis plus de 24h
    reservations_non_payees = Reservation.objects.filter(
        est_payee=False,
        date_disponibilite__lt=cutoff_time
    )
    
    for reservation in reservations_non_payees:
        livre = reservation.livre
        lecteur = reservation.lecteur
        
        # Envoyer un email pour informer l'utilisateur de l'annulation
        try:
            send_mail(
                'Votre réservation a été annulée',
                f'Bonjour {lecteur.username},\n\n'
                f'Votre réservation pour le livre "{livre.titre}" a été automatiquement annulée '
                f'car vous n\'avez pas effectué le paiement dans les 24 heures suivant sa disponibilité.\n\n'
                f'Si vous souhaitez toujours emprunter ce livre, vous devrez effectuer une nouvelle réservation.\n\n'
                f'Cordialement,\nL\'équipe BiblioSmart',
                settings.DEFAULT_FROM_EMAIL,
                [lecteur.email],
                fail_silently=True,
            )
        except Exception:
            pass  # Gérer silencieusement les erreurs d'envoi d'email
        
        # Supprimer la réservation
        reservation.delete()
        
        # Vérifier s'il y a d'autres réservations en attente pour ce livre
        next_reservation = Reservation.objects.filter(livre=livre).order_by('date_reservation').first()
        
        if next_reservation:
            # Marquer la prochaine réservation comme disponible
            next_reservation.notification_envoyee = True
            next_reservation.date_notification = timezone.now()
            next_reservation.date_disponibilite = timezone.now()
            next_reservation.save()
            
            # Envoyer un email selon que la réservation est payée ou non
            if next_reservation.est_payee:
                try:
                    send_mail(
                        'Votre livre réservé est maintenant disponible',
                        f'Bonjour {next_reservation.lecteur.username},\n\n'
                        f'Le livre "{livre.titre}" que vous avez réservé et payé est maintenant disponible. '
                        f'L\'emprunt sera automatiquement enregistré à votre nom dans 24 heures. '
                        f'Vous pourrez ensuite récupérer le livre à la bibliothèque.\n\n'
                        f'Date de disponibilité : {timezone.now().strftime("%d/%m/%Y %H:%M")}\n'
                        f'Date d\'emprunt automatique : {(timezone.now() + timedelta(hours=24)).strftime("%d/%m/%Y %H:%M")}\n\n'
                        f'Cordialement,\nL\'équipe BiblioSmart',
                        settings.DEFAULT_FROM_EMAIL,
                        [next_reservation.lecteur.email],
                        fail_silently=True,
                    )
                except Exception:
                    pass
            else:
                try:
                    send_mail(
                        'Votre livre réservé est maintenant disponible - Action requise sous 24h',
                        f'Bonjour {next_reservation.lecteur.username},\n\n'
                        f'Le livre "{livre.titre}" que vous avez réservé est maintenant disponible. '
                        f'Vous avez 24 heures pour finaliser votre réservation en effectuant le paiement de {livre.prix} MAD.\n\n'
                        f'Si vous ne procédez pas au paiement dans les 24 heures, votre réservation sera automatiquement annulée '
                        f'et le livre sera proposé au prochain lecteur en attente.\n\n'
                        f'Veuillez vous connecter à votre compte BiblioSmart pour procéder au paiement ou annuler votre réservation.\n\n'
                        f'Date limite : {(timezone.now() + timedelta(hours=24)).strftime("%d/%m/%Y %H:%M")}\n\n'
                        f'Cordialement,\nL\'équipe BiblioSmart',
                        settings.DEFAULT_FROM_EMAIL,
                        [next_reservation.lecteur.email],
                        fail_silently=True,
                    )
                except Exception:
                    pass
        else:
            # Aucune autre réservation, augmenter le stock
            livre.stock += 1
            livre.save()
