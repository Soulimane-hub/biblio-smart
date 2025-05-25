from django.apps import AppConfig


class LibraryConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'library'
    
    def ready(self):
        """
        Méthode appelée au démarrage de l'application.
        Importe les signaux et démarre le planificateur de tâches.
        """
        # Importer les signaux pour surveiller les modifications de stock
        import library.signals
        
        # Temporairement désactivé car le module apscheduler n'est pas installé
        # Pour activer, installer les modules avec:
        # pip install apscheduler django-apscheduler
        
        # import sys
        # if 'runserver' in sys.argv:
        #     from .scheduler import start
        #     start()
