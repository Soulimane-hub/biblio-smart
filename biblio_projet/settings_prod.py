from .settings import *
import os
import dj_database_url
from pathlib import Path

# SECURITY WARNING: keep the secret key used in production secret!
# Idéalement, récupérez cette valeur depuis une variable d'environnement
SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY', 'django-insecure-#fya$(xkt6x-3a*k!_-6rpmsocx_&#fwur2vn1z-dirh)=q6hr')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.environ.get('DEBUG', 'False') == 'True'

# Configuration des hôtes autorisés
ALLOWED_HOSTS = ['localhost', '127.0.0.1', '.herokuapp.com', '.up.railway.app']
if 'HEROKU_APP_NAME' in os.environ:
    ALLOWED_HOSTS.append(f"{os.environ.get('HEROKU_APP_NAME')}.herokuapp.com")

# Configuration de la base de données pour Railway
# Utilise la variable d'environnement DATABASE_URL fournie par Railway
DATABASE_URL = os.environ.get('DATABASE_URL')

# Force l'utilisation de l'URL de la base de données Railway
DATABASES = {
    'default': dj_database_url.config(default=DATABASE_URL, conn_max_age=600, ssl_require=False)
}

# Configuration des fichiers statiques
STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')

# Configuration pour servir les fichiers statiques avec WhiteNoise
MIDDLEWARE.insert(1, 'whitenoise.middleware.WhiteNoiseMiddleware')
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# Configuration des emails
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = os.environ.get('EMAIL_HOST', 'smtp.gmail.com')
EMAIL_PORT = int(os.environ.get('EMAIL_PORT', 587))
EMAIL_USE_TLS = True
EMAIL_HOST_USER = os.environ.get('EMAIL_USER', '')
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_PASSWORD', '')
DEFAULT_FROM_EMAIL = os.environ.get('DEFAULT_FROM_EMAIL', 'bibliotheque@example.com')

# Sécurité supplémentaire
SECURE_HSTS_SECONDS = 31536000  # 1 an
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_SSL_REDIRECT = False  # Désactivé pour Railway
SESSION_COOKIE_SECURE = False  # Désactivé pour Railway
CSRF_COOKIE_SECURE = True
SECURE_BROWSER_XSS_FILTER = True
X_FRAME_OPTIONS = 'DENY'
