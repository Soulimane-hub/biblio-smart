from django.contrib import admin
from django.urls import path
from django.template.response import TemplateResponse
from django.utils.html import format_html
from .models import Livre, Emprunt, Amende, Reservation, Payment, NotationUtilisateur

def library_stats_view(request):
    total_livres = Livre.objects.count()
    total_emprunts = Emprunt.objects.count()
    total_reservations = Reservation.objects.count()
    lecteurs_avec_amende = Amende.objects.filter(payee=False).values('lecteur').distinct().count()
    context = dict(
        request=request,
        total_livres=total_livres,
        total_emprunts=total_emprunts,
        total_reservations=total_reservations,
        lecteurs_avec_amende=lecteurs_avec_amende,
        title="Statistiques de la bibliothèque",
    )
    return TemplateResponse(request, "library/admin_stats.html", context)

# Ajout d'un lien dans l'index admin
admin.site.site_header = "Administration Bibliothèque"

original_index = admin.site.index

def custom_index(request, extra_context=None):
    if not extra_context:
        extra_context = {}
    extra_context['stats_link'] = True
    response = original_index(request, extra_context)
    if hasattr(response, 'template_name'):
        response.template_name = "library/admin_index.html"
    return response

admin.site.index = custom_index

original_get_urls = admin.site.get_urls

def get_urls():
    urls = original_get_urls()
    custom_urls = [
        path('library-stats/', admin.site.admin_view(library_stats_view), name='library-stats'),
    ]
    return custom_urls + urls
admin.site.get_urls = get_urls

@admin.register(Livre)
class LivreAdmin(admin.ModelAdmin):
    list_display = ('titre', 'auteur', 'categorie', 'note_display', 'annee_publication', 'isbn', 'stock', 'disponible', 'prix')
    list_filter = ('disponible', 'categorie', 'annee_publication')
    
    def note_display(self, obj):
        """Affiche la note moyenne du livre avec des étoiles.
        Si aucun utilisateur n'a noté le livre, affiche 'Aucune note'."""
        note = obj.get_note_moyenne()
        if note is None:
            return format_html('<span style="color: #999;">Aucune note</span>')
        else:
            # Convertir la note en entier avant de multiplier la chaîne
            note_entiere = int(round(note))  # Arrondir et convertir en entier
            stars = '★' * note_entiere + '☆' * (5 - note_entiere)
            return format_html('<span style="color: #FFD700;">{}</span>', stars)
    
    note_display.short_description = 'Note'
    search_fields = ('titre', 'auteur', 'isbn')
    ordering = ('titre',)
    list_editable = ('disponible', 'stock', 'prix', 'categorie')
    fieldsets = (
        ('Informations de base', {
            'fields': ('titre', 'auteur', 'isbn', 'annee_publication', 'image', 'prix')
        }),
        ('Classification', {
            'fields': ('categorie',),
            'description': 'Classement du livre'
        }),
        ('Disponibilité', {
            'fields': ('disponible', 'stock')
        }),
    )

class DemandeRetourFilter(admin.SimpleListFilter):
    title = 'Demande de retour'
    parameter_name = 'demande_retour_status'
    
    def lookups(self, request, model_admin):
        return (
            ('en_attente', 'En attente de validation'),
            ('sans_demande', 'Sans demande de retour'),
            ('retourne', 'Déjà retourné'),
        )
    
    def queryset(self, request, queryset):
        if self.value() == 'en_attente':
            return queryset.filter(demande_retour=True, est_retourne=False)
        if self.value() == 'sans_demande':
            return queryset.filter(demande_retour=False, est_retourne=False)
        if self.value() == 'retourne':
            return queryset.filter(est_retourne=True)

@admin.register(Emprunt)
class EmpruntAdmin(admin.ModelAdmin):
    list_display = ('livre', 'lecteur', 'date_emprunt', 'date_retour_prevue', 'demande_retour', 'est_retourne', 'retard', 'actions_display')
    list_filter = (DemandeRetourFilter, 'date_emprunt', 'date_retour_prevue', 'est_retourne')
    search_fields = ('livre__titre', 'livre__auteur', 'lecteur__username', 'lecteur__email')
    date_hierarchy = 'date_emprunt'
    actions = ['valider_retour_action', 'refuser_retour_action']

    def retard(self, obj):
        from django.utils import timezone
        if obj.est_retourne:
            return "Retourné"
        return "En retard" if timezone.now().date() > obj.date_retour_prevue else "En cours"
    retard.short_description = 'État'
    
    def actions_display(self, obj):
        from django.utils.html import format_html
        if obj.demande_retour and not obj.est_retourne:
            return format_html(
                '<a class="button" href="{}" style="background-color: #4CAF50; color: white; padding: 5px 10px; text-decoration: none; margin-right: 5px;">Valider</a>'
                '<a class="button" href="{}" style="background-color: #f44336; color: white; padding: 5px 10px; text-decoration: none;">Refuser</a>',
                f'/admin/library/emprunt/{obj.id}/change/?action=validate_return',
                f'/admin/library/emprunt/{obj.id}/change/?action=refuse_return'
            )
        return ""
    actions_display.short_description = 'Actions rapides'

    def valider_retour_action(self, request, queryset):
        from django.utils import timezone
        from .models import Amende
        for emprunt in queryset:
            if emprunt.demande_retour and not emprunt.est_retourne:
                emprunt.date_retour_reel = timezone.now().date()
                emprunt.est_retourne = True
                emprunt.save()
                # Générer l'amende si nécessaire
                if emprunt.date_retour_reel > emprunt.date_retour_prevue:
                    jours_retard = (emprunt.date_retour_reel - emprunt.date_retour_prevue).days
                    montant = 10 * jours_retard
                    if not Amende.objects.filter(emprunt=emprunt).exists():
                        Amende.objects.create(
                            emprunt=emprunt,
                            lecteur=emprunt.lecteur,
                            montant=montant,
                            raison=f"Retard de {jours_retard} jour(s)",
                            payee=False
                        )
                # Augmenter le stock pour déclencher le signal qui traitera les réservations
                livre = emprunt.livre
                livre.stock += 1
                livre.save()
        self.message_user(request, "Retour(s) validé(s) avec succès. Les amendes ont été générées si nécessaire.")
    valider_retour_action.short_description = "Valider le(s) retour(s) sélectionné(s)"
    
    def refuser_retour_action(self, request, queryset):
        for emprunt in queryset:
            if emprunt.demande_retour and not emprunt.est_retourne:
                # Réinitialiser la demande de retour
                emprunt.demande_retour = False
                emprunt.date_demande_retour = None
                emprunt.save()
        self.message_user(request, "Demande(s) de retour refusée(s) avec succès.")
    refuser_retour_action.short_description = "Refuser la/les demande(s) de retour sélectionnée(s)"

    def delete_model(self, request, obj):
        """Met à jour le stock du livre lorsque l'emprunt est annulé."""
        livre = obj.livre
        livre.stock += 1
        livre.save()
        super().delete_model(request, obj)

    def delete_queryset(self, request, queryset):
        """Gère la suppression en masse des emprunts."""
        for obj in queryset:
            livre = obj.livre
            livre.stock += 1
            livre.save()
        super().delete_queryset(request, queryset)


@admin.register(Amende)
class AmendeAdmin(admin.ModelAdmin):
    list_display = ('emprunt', 'montant', 'payee')
    list_filter = ('payee',)
    actions = ['marquer_comme_payee']
    
    def marquer_comme_payee(self, request, queryset):
        queryset.update(payee=True)
    marquer_comme_payee.short_description = "Marquer comme payée"

@admin.register(Reservation)
class ReservationAdmin(admin.ModelAdmin):
    list_display = ('livre', 'lecteur', 'date_reservation')
    list_filter = ('date_reservation',)
    search_fields = ('livre__titre', 'lecteur__username')

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('user', 'livre', 'amount', 'date', 'is_valid')
    list_filter = ('is_valid', 'date')
    search_fields = ('user__username', 'livre__titre')
    ordering = ('-date',)

@admin.register(NotationUtilisateur)
class NotationUtilisateurAdmin(admin.ModelAdmin):
    list_display = ('utilisateur', 'livre', 'note_display', 'date_notation')
    list_filter = ('note', 'date_notation')
    search_fields = ('utilisateur__username', 'livre__titre', 'commentaire')
    ordering = ('-date_notation',)
    
    def note_display(self, obj):
        return obj.get_note_display()
    note_display.short_description = 'Note'