from django.db.models.signals import post_save, post_init
from django.dispatch import receiver
from .models import Livre, Reservation, Emprunt
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
from datetime import timedelta
from django.db.models import F

# Dictionnaire pour stocker les valeurs de stock originales
original_stock_values = {}

@receiver(post_init, sender=Livre)
def store_original_stock(sender, instance, **kwargs):
    """
    Stocke la valeur originale du stock lorsqu'un objet Livre est initialisé.
    """
    original_stock_values[instance.pk] = instance.stock

@receiver(post_save, sender=Livre)
def process_stock_changes(sender, instance, **kwargs):
    """
    Traite les changements de stock après l'enregistrement d'un livre.
    Si le stock a augmenté, vérifie s'il y a des réservations en attente.
    """
    # Vérifier si nous avons une valeur originale pour ce livre
    if instance.pk in original_stock_values:
        old_stock = original_stock_values[instance.pk]
        
        # Si le stock a augmenté
        if instance.stock > old_stock:
            # Traiter les réservations pour chaque unité ajoutée
            process_reservations_for_book(instance, instance.stock - old_stock)
        
        # Mettre à jour la valeur originale pour la prochaine fois
        original_stock_values[instance.pk] = instance.stock

def process_reservations_for_book(livre, units_added=1):
    """
    Traite les réservations en attente pour un livre dont le stock a augmenté.
    Priorise les réservations payées (FIFO) puis les réservations non payées (FIFO).
    Convertit immédiatement les réservations payées en emprunts.
    
    Args:
        livre: L'instance du livre dont le stock a augmenté
        units_added: Le nombre d'unités ajoutées au stock
    """
    processed_units = 0
    
    # ÉTAPE 1: Traiter TOUTES les réservations payées en premier et les convertir immédiatement en emprunts
    reservations_payees = Reservation.objects.filter(
        livre=livre, 
        est_payee=True
    ).order_by('date_reservation')
    
    for reservation in reservations_payees:
        if processed_units >= units_added:
            break
            
        # Créer immédiatement l'emprunt pour cette réservation
        emprunt = Emprunt.objects.create(
            livre=livre,
            lecteur=reservation.lecteur,
            date_retour_prevue=timezone.now().date() + timedelta(days=7)
        )
        
        # Envoyer un email pour informer l'utilisateur
        try:
            send_mail(
                'Votre livre réservé est disponible pour emprunt',
                f'Bonjour {reservation.lecteur.username},\n\nLe livre "{livre.titre}" que vous avez réservé et payé est maintenant disponible. '
                f'Un emprunt a été automatiquement créé à votre nom. Vous pouvez venir récupérer le livre à la bibliothèque.\n\n'
                f'Date d\'emprunt : {timezone.now().strftime("%d/%m/%Y")}\n'
                f'Date de retour prévue : {emprunt.date_retour_prevue.strftime("%d/%m/%Y")}\n\n'
                f'Cordialement,\nL\'équipe BiblioSmart',
                settings.DEFAULT_FROM_EMAIL,
                [reservation.lecteur.email],
                fail_silently=True,
            )
        except Exception:
            pass  # Gérer silencieusement les erreurs d'envoi d'email
        
        # Supprimer la réservation car elle est maintenant transformée en emprunt
        reservation.delete()
        
        # Cette unité est traitée
        processed_units += 1
        
        # Réduire le stock car cette unité est empruntée
        livre.stock -= 1
        # Utiliser update() pour éviter de déclencher les signaux et la méthode save()
        Livre.objects.filter(pk=livre.pk).update(stock=F('stock') - 1)
    
    # ÉTAPE 2: Traiter les réservations non payées SEULEMENT si toutes les réservations payées ont été traitées
    if processed_units < units_added:
        reservations_non_payees = Reservation.objects.filter(
            livre=livre, 
            est_payee=False,
            notification_envoyee=False
        ).order_by('date_reservation')
        
        for reservation in reservations_non_payees:
            if processed_units >= units_added:
                break
                
            # Marquer la réservation comme notifiée et disponible
            reservation.notification_envoyee = True
            reservation.date_notification = timezone.now()
            reservation.date_disponibilite = timezone.now()
            reservation.save()
            
            # Envoyer un email pour informer l'utilisateur
            try:
                send_mail(
                    'Votre livre réservé est maintenant disponible - Paiement requis',
                    f'Bonjour {reservation.lecteur.username},\n\nLe livre "{livre.titre}" que vous avez réservé est maintenant disponible. '
                    f'Vous devez finaliser votre réservation en effectuant le paiement de {livre.prix} MAD pour pouvoir emprunter ce livre.\n\n'
                    f'Si vous ne procédez pas au paiement dans les 24 heures, votre réservation sera automatiquement annulée '
                    f'et le livre sera proposé au prochain lecteur en attente.\n\n'
                    f'Veuillez vous connecter à votre compte BiblioSmart pour procéder au paiement ou annuler votre réservation.\n\n'
                    f'Date limite : {(timezone.now() + timedelta(hours=24)).strftime("%d/%m/%Y %H:%M")}\n\n'
                    f'Cordialement,\nL\'équipe BiblioSmart',
                    settings.DEFAULT_FROM_EMAIL,
                    [reservation.lecteur.email],
                    fail_silently=True,
                )
            except Exception:
                pass  # Gérer silencieusement les erreurs d'envoi d'email
            
            # Cette unité est traitée
            processed_units += 1
            
    # Supprimer les réservations non payées expirées
    if processed_units < units_added:
        reservations_non_payees_expirees = Reservation.objects.filter(
            livre=livre, 
            est_payee=False,
            notification_envoyee=True,
            date_notification__lt=timezone.now() - timedelta(hours=24)
        ).order_by('date_reservation')
        
        for reservation in reservations_non_payees_expirees:
            if processed_units >= units_added:
                break
                
            # Supprimer la réservation car le délai de paiement est dépassé
            reservation.delete()
            
            # Cette unité n'est pas traitée car la réservation est annulée
            # Le stock reste augmenté
