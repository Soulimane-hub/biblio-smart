import os
import django
from django.conf import settings

# Configurer les paramètres Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'biblio_projet.settings_prod')
django.setup()

# Exécuter la commande collectstatic
from django.core.management import call_command
call_command('collectstatic', '--noinput')
print("Fichiers statiques collectés avec succès !")
