from apscheduler.schedulers.background import BackgroundScheduler
from django_apscheduler.jobstores import DjangoJobStore
from django.utils import timezone
from datetime import datetime
from .tasks import process_reservations

def start():
    """
    Démarre le planificateur de tâches pour exécuter les tâches périodiques.
    Cette fonction doit être appelée au démarrage de l'application.
    """
    scheduler = BackgroundScheduler()
    scheduler.add_jobstore(DjangoJobStore(), "default")
    
    # Exécuter la tâche de traitement des réservations toutes les heures
    scheduler.add_job(
        process_reservations,
        'interval',
        hours=1,
        name='process-reservations',
        jobstore='default',
        id='process-reservations',
        replace_existing=True,
        next_run_time=datetime.now(tz=timezone.utc)
    )
    
    scheduler.start()
