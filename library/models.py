from django.db import models
from django.contrib.auth.models import User
from datetime import timedelta
from django.utils import timezone

class Reservation(models.Model):
    livre = models.ForeignKey('Livre', on_delete=models.CASCADE)
    lecteur = models.ForeignKey(User, on_delete=models.CASCADE)
    date_reservation = models.DateTimeField(auto_now_add=True)
    est_payee = models.BooleanField(default=False)
    notification_envoyee = models.BooleanField(default=False)
    date_notification = models.DateTimeField(null=True, blank=True)
    date_disponibilite = models.DateTimeField(null=True, blank=True)  # Date à laquelle le livre devient disponible pour cette réservation
    def __str__(self):
        return f"{self.livre.titre} réservé par {self.lecteur.username}"

# === Livre ===
class Livre(models.Model):
    CATEGORIES_CHOICES = [
        ('roman', 'Roman'),
        ('science', 'Science'),
        ('histoire', 'Histoire'),
        ('biographie', 'Biographie'),
        ('informatique', 'Informatique'),
        ('art', 'Art et Culture'),
        ('jeunesse', 'Jeunesse'),
        ('poesie', 'Poésie'),
        ('autre', 'Autre'),
        ('fantasie', 'Fantasie'),
        ('drame', 'Drame'),
        ('theatre', 'Théâtre'),
        ('musique', 'Musique'),
    ]
    
    NOTE_CHOICES = [
        (1, '★'),
        (2, '★★'),
        (3, '★★★'),
        (4, '★★★★'),
        (5, '★★★★★')
    ]
    
    id = models.AutoField(primary_key=True)
    titre = models.CharField(max_length=200)
    auteur = models.CharField(max_length=200)
    isbn = models.CharField(max_length=13, unique=True, null=True, blank=True)
    stock = models.IntegerField(default=0)
    disponible = models.BooleanField(default=True)
    image = models.ImageField(upload_to='livres/', null=True, blank=True)  # Champ existant pour la compatibilité
    photo = models.ImageField(upload_to='livres/photos/', null=True, blank=True)  # Nouveau champ photo
    bibliothecaire = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    prix = models.DecimalField(max_digits=6, decimal_places=2, default=0.00)
    categorie = models.CharField(max_length=20, choices=CATEGORIES_CHOICES, default='autre')
    # La note est calculée dynamiquement à partir des NotationUtilisateur
    annee_publication = models.IntegerField(verbose_name='Année de publication', null=True, blank=True)

    def save(self, *args, **kwargs):
        # Capturer l'ancien stock si l'objet existe déjà
        old_stock = 0
        if self.pk:
            try:
                old_instance = Livre.objects.get(pk=self.pk)
                old_stock = old_instance.stock
            except Livre.DoesNotExist:
                pass
        
        # S'assurer que le stock n'est jamais négatif
        if self.stock < 0:
            self.stock = 0
            
        # Mettre à jour le champ 'disponible' en fonction du stock
        self.disponible = self.stock > 0  # Si le stock > 0, disponible = True (1), sinon False (0)
        
        # Sauvegarder d'abord l'instance
        super().save(*args, **kwargs)
        
        # Traiter les réservations si le stock a augmenté
        if self.stock > old_stock and 'update_fields' not in kwargs:
            from .signals import process_reservations_for_book
            process_reservations_for_book(self, self.stock - old_stock)

    def emprunter(self, lecteur):
        """Gère l'emprunt d'un livre."""
        if self.stock > 0:
            self.stock -= 1
            self.save()
            Emprunt.objects.create(
                livre=self,
                lecteur=lecteur,
                date_retour_prevue=timezone.now().date() + timedelta(days=7)
            )
            return True
        else:
            # Si le livre n'est pas disponible, ajoute une réservation
            if not Reservation.objects.filter(livre=self, lecteur=lecteur).exists():
                Reservation.objects.create(livre=self, lecteur=lecteur)
                return False  # Indique que le livre a été réservé
            return False  # Réservation déjà existante

    def rendre(self):
        """Gère le retour d'un livre en priorisant les réservations payées puis non payées.
        Implémente un système de file d'attente FIFO avec délais de 24h pour les actions."""
        from django.contrib.auth.models import User
        from django.core.mail import send_mail
        from django.conf import settings
        
        # Vérifie d'abord s'il y a des réservations payées
        reservation_payee = Reservation.objects.filter(livre=self, est_payee=True).order_by('date_reservation').first()
        
        if reservation_payee:
            # Pour les réservations payées, on ne crée pas l'emprunt immédiatement
            # On notifie l'utilisateur et on créera l'emprunt après 24h
            reservation_payee.notification_envoyee = True
            reservation_payee.date_notification = timezone.now()
            reservation_payee.date_disponibilite = timezone.now()
            reservation_payee.save()
            
            # Envoyer un email pour informer l'utilisateur
            try:
                send_mail(
                    'Votre livre réservé est maintenant disponible',
                    f'Bonjour {reservation_payee.lecteur.username},\n\nLe livre "{self.titre}" que vous avez réservé et payé est maintenant disponible. '
                    f'L\'emprunt sera automatiquement enregistré à votre nom dans 24 heures. Vous pourrez ensuite récupérer le livre à la bibliothèque.\n\n'
                    f'Date de disponibilité : {timezone.now().strftime("%d/%m/%Y %H:%M")}\n'
                    f'Date d\'emprunt automatique : {(timezone.now() + timedelta(hours=24)).strftime("%d/%m/%Y %H:%M")}\n\n'
                    f'Cordialement,\nL\'équipe BiblioSmart',
                    settings.DEFAULT_FROM_EMAIL,
                    [reservation_payee.lecteur.email],
                    fail_silently=True,
                )
            except Exception:
                pass  # Gérer silencieusement les erreurs d'envoi d'email
            
            # Ne pas augmenter le stock car le livre est réservé
            # L'emprunt sera créé automatiquement par une tâche planifiée après 24h
        else:
            # S'il n'y a pas de réservation payée, vérifier les réservations non payées
            reservation_non_payee = Reservation.objects.filter(livre=self, est_payee=False).order_by('date_reservation').first()
            
            if reservation_non_payee:
                # Marquer la réservation comme notifiée et disponible
                reservation_non_payee.notification_envoyee = True
                reservation_non_payee.date_notification = timezone.now()
                reservation_non_payee.date_disponibilite = timezone.now()
                reservation_non_payee.save()
                
                # Créer une notification pour informer l'utilisateur
                date_limite = timezone.now() + timedelta(hours=24)
                Notification.objects.create(
                    user=reservation_non_payee.lecteur,
                    title='Livre disponible - Action requise sous 24h',
                    message=f'Le livre "{self.titre}" que vous avez réservé est maintenant disponible. '
                            f'Vous avez 24 heures pour finaliser votre réservation en effectuant le paiement de {self.prix} MAD. '
                            f'Si vous ne procédez pas au paiement avant le {date_limite.strftime("%d/%m/%Y %H:%M")}, '
                            f'votre réservation sera automatiquement annulée et le livre sera proposé au prochain lecteur en attente.',
                    notification_type='disponible',
                    link=reverse('book_details', args=[self.id])
                )
                
                # Augmenter temporairement le stock pour permettre l'emprunt après paiement
                # Si le paiement n'est pas effectué dans les 24h, la réservation sera annulée
                # par une tâche planifiée et le livre sera proposé au prochain lecteur
                self.stock += 1
                self.save()
            else:
                # Aucune réservation, augmenter simplement le stock
                self.stock += 1
                self.save()
            
    def get_note_moyenne(self):
        """Calcule la note moyenne du livre à partir des notations des utilisateurs."""
        from django.db.models import Avg
        moyenne = self.notations.aggregate(Avg('note'))['note__avg']
        return moyenne if moyenne else 0
        
    def __str__(self):
        return self.titre
        
    
# === Emprunt ===
class Emprunt(models.Model):
    livre = models.ForeignKey('Livre', on_delete=models.CASCADE)
    lecteur = models.ForeignKey(User, on_delete=models.CASCADE)
    date_emprunt = models.DateField(auto_now_add=True)
    date_retour_prevue = models.DateField()
    date_retour_reel = models.DateField(null=True, blank=True)  # Date réelle de retour
    est_retourne = models.BooleanField(default=False)  # Si le livre a été retourné
    retour_valide_admin = models.BooleanField(default=False)  # Si le retour a été validé par un administrateur
    demande_retour = models.BooleanField(default=False)  # Si le lecteur a demandé à retourner le livre
    date_demande_retour = models.DateTimeField(null=True, blank=True)  # Date de la demande de retour

    def __str__(self):
        return f"{self.livre.titre} emprunté par {self.lecteur.username} (prix : {self.livre.prix} MAD)"
# === Amende ===
class Amende(models.Model):
    id = models.AutoField(primary_key=True)
    emprunt = models.OneToOneField(Emprunt, on_delete=models.CASCADE)
    lecteur = models.ForeignKey(User, on_delete=models.CASCADE)
    montant = models.DecimalField(max_digits=6, decimal_places=2)
    montant_paye = models.DecimalField(max_digits=6, decimal_places=2, default=0.00)  
    raison = models.CharField(max_length=100)
    payee = models.BooleanField(default=False)  # Champ pour indiquer si l'amende a été payée
    
    def __str__(self):
        return f"Amende de {self.montant} MAD pour {self.lecteur.username}"

# === Historique des emprunts ===
class HistoriqueEmprunt(models.Model):
    ACTION_CHOICES = [
        ('emprunt', 'Emprunt'),
        ('demande_retour', 'Demande de retour'),
        ('retour_valide', 'Retour validé'),
        ('retour_refuse', 'Retour refusé'),
        ('amende', 'Amende générée'),
        ('paiement_amende', 'Paiement d\'amende'),
    ]
    
    emprunt = models.ForeignKey(Emprunt, on_delete=models.CASCADE, related_name='historique')
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    date_action = models.DateTimeField(auto_now_add=True)
    commentaire = models.TextField(blank=True, null=True)
    utilisateur = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    
    class Meta:
        ordering = ['-date_action']
        verbose_name = "Historique d'emprunt"
        verbose_name_plural = "Historiques d'emprunts"
    
    def __str__(self):
        return f"{self.get_action_display()} - {self.emprunt.livre.titre} - {self.date_action.strftime('%d/%m/%Y %H:%M')}"


# === Payment ===
class Payment(models.Model):
    description = models.CharField(max_length=50, blank=True, help_text="Type de paiement : emprunt, reservation, amende")
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    livre = models.ForeignKey(Livre, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=6, decimal_places=2)
    date = models.DateTimeField(auto_now_add=True)
    is_valid = models.BooleanField(default=False)
    emprunt = models.OneToOneField('Emprunt', on_delete=models.CASCADE, null=True, blank=True, related_name='paiement')
    reservation = models.OneToOneField('Reservation', on_delete=models.CASCADE, null=True, blank=True, related_name='paiement')

    def __str__(self):
        return f"Paiement de {self.amount} MAD pour {self.livre.titre} par {self.user.username} le {self.date.strftime('%Y-%m-%d')}"

# === RetourLivre ===
class RetourLivre(models.Model):
    STATUT_CHOICES = [
        ('en_attente', 'En attente'),
        ('valide', 'Validé'),
        ('refuse', 'Refusé')
    ]
    
    emprunt = models.ForeignKey(Emprunt, on_delete=models.CASCADE, related_name='retours')
    date_demande = models.DateTimeField(auto_now_add=True)
    date_validation = models.DateTimeField(null=True, blank=True)
    statut = models.CharField(max_length=20, choices=STATUT_CHOICES, default='en_attente')
    
    def __str__(self):
        return f"Demande de retour pour {self.emprunt.livre.titre} par {self.emprunt.lecteur.username}"

# === Notation utilisateur ===
class NotationUtilisateur(models.Model):
    NOTE_CHOICES = [
        (1, '★'),
        (2, '★★'),
        (3, '★★★'),
        (4, '★★★★'),
        (5, '★★★★★')
    ]
    
    livre = models.ForeignKey(Livre, on_delete=models.CASCADE, related_name='notations')
    utilisateur = models.ForeignKey(User, on_delete=models.CASCADE)
    note = models.IntegerField(choices=NOTE_CHOICES)
    commentaire = models.TextField(blank=True, null=True)
    date_notation = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('livre', 'utilisateur')
        verbose_name = "Notation utilisateur"
        verbose_name_plural = "Notations utilisateurs"
    
    def __str__(self):
        return f"{self.utilisateur.username} a noté {self.livre.titre} : {self.get_note_display()}"
