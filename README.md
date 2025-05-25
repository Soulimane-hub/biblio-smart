# BiblioSmart - Système de Gestion de Bibliothèque

BiblioSmart est une application web de gestion de bibliothèque développée avec Django. Elle permet de gérer les livres, les emprunts, les réservations et les utilisateurs.

## Fonctionnalités

- Gestion des livres (ajout, modification, suppression)
- Gestion des emprunts et des réservations
- Système de paiement pour les réservations
- Notifications par email
- Tableau de bord administratif
- Filtrage par catégories
- Recherche de livres par titre, auteur ou ISBN
- Gestion des amendes pour retards
- Système de notation et d'avis sur les livres
- Interface utilisateur moderne et responsive

## Prérequis pour le déploiement sur Heroku

- [Compte Heroku](https://signup.heroku.com/) (gratuit pour commencer)
- [Git](https://git-scm.com/downloads) installé sur votre ordinateur
- [Heroku CLI](https://devcenter.heroku.com/articles/heroku-cli) installé sur votre ordinateur
- Python 3.10+ (compatible avec Heroku)

## Guide de déploiement sur Heroku

### 1. Préparation du projet

Votre projet BiblioSmart est déjà configuré pour Heroku avec les fichiers suivants :

- `Procfile` : Définit la commande pour démarrer l'application
- `runtime.txt` : Spécifie la version de Python à utiliser
- `requirements.txt` : Liste toutes les dépendances
- `biblio_projet/settings_prod.py` : Paramètres de production
- `.gitignore` : Fichiers à exclure du dépôt Git
- `init_heroku_db.py` : Script d'initialisation de la base de données
### 2. Initialisation du dépôt Git

Si vous n'avez pas encore initialisé Git dans votre projet, suivez ces étapes :

```bash
# Ouvrez un terminal dans le répertoire de votre projet
cd c:\Users\pc\Desktop\biblio_projet_issam

# Initialisez un dépôt Git
git init

# Ajoutez tous les fichiers au dépôt Git
git add .

# Créez un commit initial
git commit -m "Version initiale pour déploiement Heroku"
```

### 3. Création de l'application Heroku

```bash
# Connectez-vous à Heroku (une fenêtre de navigateur s'ouvrira)
heroku login

# Créez une nouvelle application Heroku (remplacez 'bibliosmart' par le nom souhaité)
heroku create bibliosmart

# Vérifiez que Heroku a été ajouté comme remote
git remote -v
```
### 4. Configuration des variables d'environnement

```bash
# Définir le module de paramètres à utiliser
heroku config:set DJANGO_SETTINGS_MODULE=biblio_projet.settings_prod

# Définir une clé secrète sécurisée (remplacez par une clé complexe)
heroku config:set DJANGO_SECRET_KEY="votre_clé_secrète_très_longue_et_complexe"

# Désactiver temporairement la collecte des fichiers statiques
heroku config:set DISABLE_COLLECTSTATIC=1
```

### 5. Ajout de la base de données PostgreSQL

```bash
# Ajouter la base de données PostgreSQL (plan gratuit)
heroku addons:create heroku-postgresql:mini
```
### 6. Déploiement de l'application

```bash
# Pousser votre code vers Heroku
git push heroku master
```

Si vous utilisez la branche `main` au lieu de `master` :

```bash
git push heroku main
```

### 7. Initialisation de la base de données

```bash
# Exécuter les migrations
heroku run python manage.py migrate

# Exécuter le script d'initialisation
heroku run python init_heroku_db.py

# Collecter les fichiers statiques
heroku run python manage.py collectstatic --noinput
```
### 8. Ouvrir et vérifier l'application

```bash
# Ouvrir l'application dans le navigateur
heroku open
```

### 9. Vérifier les journaux en cas de problème

```bash
# Afficher les journaux en temps réel
heroku logs --tail
```

### 10. Commandes utiles pour la maintenance

```bash
# Redémarrer l'application
heroku restart

# Exécuter une commande shell sur Heroku
heroku run bash

# Sauvegarder la base de données
heroku pg:backups:capture

# Télécharger la dernière sauvegarde
heroku pg:backups:download
```

### 11. Mise à jour de l'application après modifications

Après avoir fait des modifications locales :

```bash
# Ajouter les modifications
git add .

# Créer un commit
git commit -m "Description des modifications"

# Déployer les modifications
git push heroku master  # ou main selon votre branche
```

## Résolution des problèmes courants

### Erreur lors du déploiement

**Problème** : L'application ne se déploie pas correctement.

**Solution** : Vérifiez les journaux pour identifier l'erreur :
```bash
heroku logs --tail
```

### Erreur de base de données

**Problème** : Erreurs liées à la base de données PostgreSQL.

**Solution** : Vérifiez que l'add-on PostgreSQL est bien installé :
```bash
heroku addons
```

### Problèmes avec les fichiers statiques

**Problème** : Les fichiers CSS/JS ne s'affichent pas correctement.

**Solution** : Assurez-vous d'avoir exécuté la commande collectstatic :
```bash
heroku run python manage.py collectstatic --noinput
```

### Erreur H10 (App crashed)

**Problème** : L'application plante au démarrage.

**Solution** : Vérifiez le Procfile et les logs :
```bash
heroku logs --tail
```

## Fonctionnalités spécifiques de BiblioSmart

### Système de réservation et de paiement

BiblioSmart propose un système complet de réservation et de paiement :
- Réservation de livres sans paiement immédiat
- Option "Réserver et payer" pour finaliser immédiatement
- Conversion automatique des réservations payées en emprunts lorsque le livre devient disponible
- Notifications par email pour informer les utilisateurs

### Gestion des amendes

Le système gère automatiquement les amendes pour les retards :
- Calcul automatique des amendes en fonction du nombre de jours de retard
- Blocage des emprunts et réservations pour les utilisateurs ayant des amendes non payées
- Interface de paiement des amendes

### Tableau de bord administratif

Un tableau de bord complet pour les administrateurs permet de :
- Gérer les livres (ajout, modification, suppression)
- Suivre les emprunts et les retours
- Valider les demandes de retour
- Gérer les utilisateurs
- Consulter les statistiques

## Variables d'environnement requises

- `DJANGO_SETTINGS_MODULE` : Module de paramètres à utiliser (biblio_projet.settings_prod)
- `SECRET_KEY` : Clé secrète pour Django
- `DB_NAME` : Nom de la base de données
- `DB_USER` : Nom d'utilisateur de la base de données
- `DB_PASSWORD` : Mot de passe de la base de données
- `DB_HOST` : Hôte de la base de données
- `DB_PORT` : Port de la base de données
- `EMAIL_HOST` : Serveur SMTP pour les emails
- `EMAIL_PORT` : Port du serveur SMTP
- `EMAIL_USER` : Adresse email pour l'envoi
- `EMAIL_PASSWORD` : Mot de passe de l'email
- `DEFAULT_FROM_EMAIL` : Adresse d'expéditeur par défaut

## Maintenance

- Assurez-vous de sauvegarder régulièrement votre base de données
- Mettez à jour les dépendances régulièrement pour des raisons de sécurité
- Surveillez les logs pour détecter d'éventuels problèmes

## Contact et support

Pour toute question ou assistance concernant le déploiement ou l'utilisation de BiblioSmart :

- **Email** : support@bibliosmart.ma
- **Site web** : [www.bibliosmart.ma](https://www.bibliosmart.ma)

## Remerciements

Merci d'utiliser BiblioSmart pour la gestion de votre bibliothèque. Nous espérons que cette application vous sera utile et facilite votre travail quotidien.
