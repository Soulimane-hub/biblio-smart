import os
import django
import sys

# Configurer les paramètres Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'biblio_projet.settings_prod')
django.setup()

print("Initialisation de la base de données PostgreSQL sur Heroku...")

# Vérifier si la variable DATABASE_URL est définie
db_url = os.environ.get('DATABASE_URL')
if not db_url:
    print("Erreur: La variable d'environnement DATABASE_URL n'est pas définie.")
    print("Assurez-vous d'avoir ajouté l'add-on PostgreSQL à votre application Heroku.")
    sys.exit(1)

print("Configuration de la base de données détectée.")


# Exécuter les migrations Django
print("\nExécution des migrations...")
from django.core.management import call_command
call_command('migrate')

print("\nCréation d'un superutilisateur...")
from django.contrib.auth.models import User
if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser('admin', 'admin@example.com', 'admin_password')
    print("Superutilisateur créé avec succès!")
    print("Nom d'utilisateur: admin")
    print("Mot de passe: admin_password")
    print("N'oubliez pas de changer ce mot de passe après le premier login!")
else:
    print("Un utilisateur avec le nom 'admin' existe déjà.")

# Initialiser les catégories de livres
print("\nInitialisation des catégories de livres...")
from library.models import Livre

# Liste des catégories définies dans le modèle Livre
categories = [
    'roman', 'science', 'histoire', 'biographie', 'informatique',
    'art', 'jeunesse', 'poesie', 'autre', 'fantasie', 'drame',
    'theatre', 'musique', 'policier'
]

# Créer un livre exemple pour chaque catégorie si la catégorie n'a pas de livre
for categorie in categories:
    if not Livre.objects.filter(categorie=categorie).exists():
        print(f"Création d'un livre exemple pour la catégorie '{categorie}'")
        Livre.objects.create(
            titre=f"Exemple de livre - {categorie.capitalize()}",
            auteur="BiblioSmart",
            categorie=categorie,
            stock=5,
            prix=100.00,
            disponible=True,
            isbn=f"ISBN-{categorie[:3]}-{categorie[-3:]}"
        )

print("\nInitialisation de la base de données terminée!")
