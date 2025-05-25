from django.urls import path
from . import views
from . import api_views
from . import views_dashboard
from django.contrib.auth.views import LogoutView

from library.receipt_generator import download_receipt

urlpatterns = [
    path('notifications/', views.notifications, name='notifications'),
    path('livre/<int:livre_id>/payer/', views.payer_livre, name='payer_livre'),
    path('livre/<int:livre_id>/reserver/', views.reserver_livre, name='reserver_livre'),
    path('', views.register, name='register'),
    path('home/', views.home, name='home'),
    path('book/<int:livre_id>/', views.book_details, name='book_details'),
    path('book/<int:livre_id>/json/', api_views.book_details_json, name='book_details_json'),
    path('history/', views.history, name='history'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('emprunt/<int:emprunt_id>/annuler/', views.annuler_emprunt, name='annuler_emprunt'),
    path('emprunt/<int:emprunt_id>/valider_retour/', views.valider_retour, name='valider_retour'),
    path('reservation/<int:reservation_id>/annuler/', views.annuler_reservation, name='annuler_reservation'),
    path('download_receipt/<int:paiement_id>/', download_receipt, name='download_receipt'),
    path('payer_reservation/<int:reservation_id>/', views.payer_reservation, name='payer_reservation'),
    path('payer_emprunt/<int:reservation_id>/', views.payer_emprunt, name='payer_emprunt'),
    path('payer_amende/<int:amende_id>/', views.payer_amende, name='payer_amende'),
    path('clear_amende_session/', views.clear_amende_session, name='clear_amende_session'),
    path('logout/', LogoutView.as_view(next_page='register'), name='logout'),
    # Nouvelles routes pour le dashboard
    path('ajouter-livre/', views.ajouter_livre, name='ajouter_livre'),
    path('modifier-livre/<int:livre_id>/', views.modifier_livre, name='modifier_livre'),
    path('valider-retour-livre/', views.valider_retour_livre, name='valider_retour_livre'),
    path('gerer-utilisateur/', views.gerer_utilisateur, name='gerer_utilisateur'),
    # Routes pour les sections séparées du dashboard
    path('dashboard/users/', views.dashboard_users, name='dashboard_users'),
    path('dashboard/books/', views.dashboard_books, name='dashboard_books'),
    path('dashboard/loans/', views.dashboard_loans, name='dashboard_loans'),
    path('dashboard/reservations/', views.dashboard_reservations, name='dashboard_reservations'),
    path('dashboard/reviews/', views.dashboard_reviews, name='dashboard_reviews'),
    path('dashboard/return-requests/', views_dashboard.dashboard_return_requests, name='dashboard_return_requests'),
    
    # Route pour la suppression des avis
    path('delete-review/<int:review_id>/', views.delete_review, name='delete_review'),
    
    # Route pour le retour des livres
    path('return-book/<int:emprunt_id>/', views.return_book, name='return_book'),
    
    # Route pour refuser une demande de retour
    path('refuse-return-request/<int:emprunt_id>/', views.refuse_return, name='refuse_return_request'),
    
    # Route simplifiée pour refuser un retour
    path('refuse-return-simple/<int:emprunt_id>/', views.refuse_return_simple, name='refuse_return_simple'),
    
    # Route pour valider une demande de retour
    path('validate-return/<int:emprunt_id>/', views.validate_return, name='validate_return'),
    
    # Route simplifiée pour valider un retour
    path('validate-return-simple/<int:emprunt_id>/', views.validate_return_simple, name='validate_return_simple'),
    
    # Route pour valider une demande de retour via AJAX sans redirection
    path('validate-return-ajax/<int:emprunt_id>/', views.validate_return_ajax, name='validate_return_ajax'),
    
    # Routes pour la gestion des photos des livres
    path('dashboard/book-photos/', views_dashboard.dashboard_book_photos, name='dashboard_book_photos'),
    path('manage-book-photos/<int:livre_id>/', views_dashboard.manage_book_photos, name='manage_book_photos'),
    
    # Route pour l'historique des emprunts
    path('dashboard/emprunt-history/', views.emprunt_history, name='emprunt_history'),
    
    # Demandes de retour
    path('request-return/<int:emprunt_id>/', views.request_return, name='request_return'),
    path('validate-return/<int:emprunt_id>/', views.validate_return, name='validate_return'),
    path('refuse-return/<int:emprunt_id>/', views.refuse_return, name='refuse_return'),
    path('debug-return-requests/', views_dashboard.debug_return_requests, name='debug_return_requests'),
    
    # Routes API pour les utilisateurs
    path('api/users/<int:user_id>/', views.api_users, name='api_users'),
    path('api/users/add/', views.api_users_add, name='api_users_add'),
    path('api/users/<int:user_id>/edit/', views.api_users_edit, name='api_users_edit'),
    path('api/users/<int:user_id>/delete/', views.api_users_delete, name='api_users_delete'),
    
    # Routes API pour les réservations
    path('api/reservations/<int:reservation_id>/validate/', views.api_reservations_validate, name='api_reservations_validate'),
]