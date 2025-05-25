from django.db.models.signals import post_save, post_init
from django.dispatch import receiver
from .models import Livre, Reservation, Emprunt
from django.utils import timezone
from django.core.mail import send_mail
from django.db import transaction
from datetime import timedelta
from django.conf import settings
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


@receiver(post_save, sender=Reservation)
def process_paid_reservation(sender, instance, **kwargs):
    """
    Traite automatiquement les réservations payées en les convertissant en emprunts
    """
    # Vérifier si la réservation est payée
    if instance.est_payee:
        print(f"Traitement automatique de la réservation payée ID: {instance.pk} pour le livre '{instance.livre.titre}'")
        
        # Obtenir le livre associé à la réservation
        livre = instance.livre
        
        # Créer un emprunt pour cette réservation
        try:
            with transaction.atomic():
                # Créer un emprunt pour cette réservation
                emprunt = Emprunt.objects.create(
                    livre=livre,
                    lecteur=instance.lecteur,
                    date_emprunt=timezone.now(),
                    date_retour_prevue=timezone.now() + timedelta(days=7),
                    retour_valide_admin=False  # Pas encore retourné
                )
                
                print(f"Emprunt créé: ID {emprunt.pk}")
                
                # Réduire le stock du livre si nécessaire
                if livre.stock > 0:
                    livre.stock -= 1
                    if livre.stock <= 0:
                        livre.disponible = False
                    livre.save(update_fields=['stock', 'disponible'])
                    print(f"Stock du livre mis à jour: {livre.stock}")
                
                # Si la réservation a un paiement associé, le transférer à l'emprunt
                try:
                    payment = instance.paiement
                    if payment:
                        payment.emprunt = emprunt
                        payment.reservation = None
                        payment.description = f"Conversion de réservation en emprunt pour '{livre.titre}'"
                        payment.save()
                        print(f"Paiement {payment.id} transféré de la réservation à l'emprunt")
                except Exception as e:
                    print(f"Erreur lors du transfert du paiement: {str(e)}")
                
                # Envoyer un email pour informer l'utilisateur
                try:
                    send_mail(
                        'Votre livre réservé est maintenant emprunté',
                        f'Bonjour {instance.lecteur.username},\n\n'
                        f'Le livre "{livre.titre}" que vous avez réservé et payé a été automatiquement ajouté à vos emprunts. '
                        f'Vous n\'avez pas besoin de payer à nouveau car vous avez déjà payé lors de la réservation.\n\n'
                        f'Vous devez retourner le livre avant le {emprunt.date_retour_prevue.strftime("%d/%m/%Y")}.\n\n'
                        f'Cordialement,\nL\'équipe BiblioSmart',
                        settings.DEFAULT_FROM_EMAIL,
                        [instance.lecteur.email],
                        fail_silently=True,
                    )
                    print(f"Email envoyé à {instance.lecteur.email}")
                except Exception as e:
                    print(f"Erreur lors de l'envoi de l'email: {str(e)}")  # Log l'erreur pour débogage
                    
                # Créer une notification dans l'application si la classe existe
                try:
                    from django.apps import apps
                    Notification = apps.get_model('library', 'Notification')
                    Notification.objects.create(
                        user=instance.lecteur,
                        title='Livre emprunté',
                        message=f"Le livre {livre.titre} a été automatiquement ajouté à vos emprunts. Vous devez le retourner avant le {emprunt.date_retour_prevue.strftime('%d/%m/%Y')}.",
                        notification_type='emprunt',
                        link=f"/book/{livre.id}/"
                    )
                    print(f"Notification créée pour l'utilisateur {instance.lecteur.username}")
                except Exception as e:
                    print(f"Erreur lors de la création de la notification: {str(e)}")  # Log l'erreur pour débogage
                
                # Supprimer la réservation car elle est maintenant convertie en emprunt
                instance_id = instance.pk
                instance.delete()
                print(f"Réservation {instance_id} supprimée après conversion en emprunt")
                
        except Exception as e:
            print(f"Erreur lors du traitement de la réservation {instance.pk}: {str(e)}")


def process_reservations_for_book(livre, units_added=1):
    """
    Traite les réservations en attente pour un livre dont le stock a augmenté.
    Priorise les réservations payées (FIFO) puis les réservations non payées (FIFO).
    Convertit immédiatement les réservations payées en emprunts et envoie des notifications.
    
    Args:
        livre: L'instance du livre dont le stock a augmenté
        units_added: Le nombre d'unités ajoutées au stock
    """
    print(f"Traitement des réservations pour le livre '{livre.titre}' (ID: {livre.id}), {units_added} unité(s) ajoutée(s), stock actuel: {livre.stock}")
    
    # Compteur d'unités traitées
    processed_units = 0
    
    # Vérifier si le livre a un stock disponible
    if livre.stock <= 0:
        print(f"Aucun stock disponible pour le livre '{livre.titre}', traitement annulé")
        return processed_units
        
    # Vérifier s'il y a des réservations en attente pour ce livre
    reservations_count = Reservation.objects.filter(livre=livre).count()
    
    # Si aucune réservation, marquer le livre comme disponible et terminer
    if reservations_count == 0:
        if not livre.disponible and livre.stock > 0:
            livre.disponible = True
            livre.save()
            print(f"Le livre '{livre.titre}' est marqué comme disponible car il n'y a pas de réservations en attente")
        return processed_units
    
    # ÉTAPE 1: Traiter d'abord les réservations payées
    reservations_payees = Reservation.objects.filter(
        livre=livre, 
        est_payee=True
    ).order_by('date_reservation')
    
    print(f"Nombre de réservations payées en attente: {reservations_payees.count()}")
    
    # Forcer le traitement des réservations payées même si le stock est épuisé
    # car nous voulons qu'elles soient automatiquement converties en emprunts
    if reservations_payees.exists() and livre.stock <= 0:
        print(f"Stock épuisé mais traitement forcé des réservations payées pour le livre '{livre.titre}'")
        # Augmenter temporairement le stock pour permettre le traitement
        livre.stock += 1
        livre.save()
    
    for reservation in reservations_payees:
        # Vérifier à nouveau le stock à chaque itération
        if processed_units >= units_added or livre.stock <= 0:
            print(f"Arrêt du traitement des réservations payées: units_added={units_added}, processed_units={processed_units}, stock={livre.stock}")
            break
        
        print(f"Traitement de la réservation payée ID: {reservation.pk} pour l'utilisateur {reservation.lecteur.username}")
        
        try:
            # Créer un emprunt pour cette réservation dans une transaction
            with transaction.atomic():
                # Créer un emprunt pour cette réservation
                emprunt = Emprunt.objects.create(
                    livre=livre,
                    lecteur=reservation.lecteur,
                    date_emprunt=timezone.now(),
                    date_retour_prevue=timezone.now() + timedelta(days=7),
                    retour_valide_admin=False  # Pas encore retourné
                )
                
                print(f"Emprunt créé: ID {emprunt.pk}")
                
                # Réduire le stock du livre
                livre.stock -= 1
                if livre.stock <= 0:
                    livre.disponible = False
                livre.save()
                
                print(f"Stock du livre mis à jour: {livre.stock}")
                
                # Supprimer la réservation car elle est maintenant convertie en emprunt
                reservation_id = reservation.pk
                user_email = reservation.lecteur.email
                user_name = reservation.lecteur.username
                
                # Si la réservation a un paiement associé, le transférer à l'emprunt
                try:
                    payment = reservation.paiement
                    if payment:
                        payment.emprunt = emprunt
                        payment.reservation = None
                        payment.description = f"Conversion de réservation en emprunt pour '{livre.titre}'"
                        payment.save()
                        print(f"Paiement {payment.id} transféré de la réservation à l'emprunt")
                except Exception as e:
                    print(f"Erreur lors du transfert du paiement: {str(e)}")
                
                reservation.delete()
                print(f"Réservation {reservation_id} supprimée après conversion en emprunt")
                
                # Envoyer un email pour informer l'utilisateur
                try:
                    send_mail(
                        'Votre livre réservé est maintenant emprunté',
                        f'Bonjour {user_name},\n\n'
                        f'Le livre "{livre.titre}" que vous avez réservé et payé a été automatiquement ajouté à vos emprunts. '
                        f'Vous n\'avez pas besoin de payer à nouveau car vous avez déjà payé lors de la réservation.\n\n'
                        f'Vous devez retourner le livre avant le {emprunt.date_retour_prevue.strftime("%d/%m/%Y")}.\n\n'
                        f'Cordialement,\nL\'\u00e9quipe BiblioSmart',
                        settings.DEFAULT_FROM_EMAIL,
                        [user_email],
                        fail_silently=True,
                    )
                    print(f"Email envoyé à {user_email}")
                except Exception as e:
                    print(f"Erreur lors de l'envoi de l'email: {str(e)}")  # Log l'erreur pour débogage
                    
                # Créer une notification dans l'application si la classe existe
                try:
                    from django.apps import apps
                    Notification = apps.get_model('library', 'Notification')
                    Notification.objects.create(
                        user=reservation.lecteur,
                        title='Livre emprunté',
                        message=f"Le livre {livre.titre} a été automatiquement ajouté à vos emprunts. Vous devez le retourner avant le {emprunt.date_retour_prevue.strftime('%d/%m/%Y')}.",
                        notification_type='emprunt',
                        link=f"/book/{livre.id}/"
                    )
                    print(f"Notification créée pour l'utilisateur {user_name}")
                except Exception as e:
                    print(f"Erreur lors de la création de la notification: {str(e)}")  # Log l'erreur pour débogage
                
                # Cette unité est traitée
                processed_units += 1
        except Exception as e:
            print(f"Erreur lors du traitement de la réservation {reservation.pk}: {str(e)}")
        
        # Vérifier si le stock est épuisé
        if livre.stock <= 0:
            livre.disponible = False
            Livre.objects.filter(pk=livre.pk).update(disponible=False)
            print(f"Le livre '{livre.titre}' est maintenant marqué comme indisponible")
            break
    
    # ÉTAPE 2: Traiter les réservations non payées SEULEMENT si toutes les réservations payées ont été traitées
    if processed_units < units_added and livre.stock > 0:
        reservations_non_payees = Reservation.objects.filter(
            livre=livre, 
            est_payee=False,
            notification_envoyee=False
        ).order_by('date_reservation')
        
        print(f"Nombre de réservations non payées en attente: {reservations_non_payees.count()}")
        
        for reservation in reservations_non_payees:
            if processed_units >= units_added or livre.stock <= 0:
                print(f"Arrêt du traitement des réservations non payées: units_added={units_added}, processed_units={processed_units}, stock={livre.stock}")
                break
                
            print(f"Traitement de la réservation non payée ID: {reservation.pk} pour l'utilisateur {reservation.lecteur.username}")
            
            # Marquer la réservation comme notifiée et disponible
            reservation.notification_envoyee = True
            reservation.date_notification = timezone.now()
            reservation.date_disponibilite = timezone.now()
            reservation.save()
            
            print(f"Réservation {reservation.pk} marquée comme notifiée")
            
            # Envoyer un email pour informer l'utilisateur
            try:
                send_mail(
                    'Votre livre réservé est maintenant disponible - Paiement requis',
                    f'Bonjour {reservation.lecteur.username},\n\nLe livre "{livre.titre}" que vous avez réservé est maintenant disponible. '
                    f'Vous devez finaliser votre emprunt en effectuant le paiement de {livre.prix} MAD pour pouvoir emprunter ce livre.\n\n'
                    f'Si vous ne procédez pas au paiement dans les 24 heures, votre réservation sera automatiquement annulée '
                    f'et le livre sera proposé au prochain lecteur en attente.\n\n'
                    f'Veuillez vous connecter à votre compte BiblioSmart pour procéder au paiement ou annuler votre réservation.\n\n'
                    f'Date limite : {(timezone.now() + timedelta(hours=24)).strftime("%d/%m/%Y %H:%M")}\n\n'
                    f'Cordialement,\nL\'\u00e9quipe BiblioSmart',
                    settings.DEFAULT_FROM_EMAIL,
                    [reservation.lecteur.email],
                    fail_silently=True,
                )
                print(f"Email envoyé à {reservation.lecteur.email}")
            except Exception as e:
                print(f"Erreur lors de l'envoi de l'email: {str(e)}")  # Log l'erreur pour débogage
            
            # Cette unité est traitée, mais ne réduit pas le stock car c'est juste une notification
            processed_units += 1
            
    # ÉTAPE 3: Supprimer les réservations non payées expirées
    reservations_non_payees_expirees = Reservation.objects.filter(
        livre=livre, 
        est_payee=False,
        notification_envoyee=True,
        date_notification__lt=timezone.now() - timedelta(hours=24)
    ).order_by('date_reservation')
    
    expired_count = reservations_non_payees_expirees.count()
    if expired_count > 0:
        print(f"Suppression de {expired_count} réservations non payées expirées pour le livre '{livre.titre}'")
        
        for reservation in reservations_non_payees_expirees:
            reservation_id = reservation.pk
            user_email = reservation.lecteur.email
            
            # Envoyer un email pour informer l'utilisateur de l'annulation
            try:
                send_mail(
                    'Votre réservation a été annulée',
                    f'Bonjour {reservation.lecteur.username},\n\n'
                    f'Votre réservation pour le livre "{livre.titre}" a été annulée car le délai de paiement de 24 heures est dépassé.\n\n'
                    f'Si vous souhaitez toujours emprunter ce livre, vous devrez effectuer une nouvelle réservation.\n\n'
                    f'Cordialement,\nL\'\u00e9quipe BiblioSmart',
                    settings.DEFAULT_FROM_EMAIL,
                    [user_email],
                    fail_silently=True,
                )
            except Exception as e:
                print(f"Erreur lors de l'envoi de l'email d'annulation: {str(e)}")  # Log l'erreur pour débogage
            
            # Supprimer la réservation car le délai de paiement est dépassé
            reservation.delete()
            print(f"Réservation expirée {reservation_id} supprimée")
    
    print(f"Traitement des réservations terminé. Unités traitées: {processed_units}/{units_added}, stock final: {livre.stock}")
    return processed_units
