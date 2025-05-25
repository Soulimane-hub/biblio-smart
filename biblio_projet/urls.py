"""
URL configuration for biblio_projet project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.shortcuts import redirect
from django.contrib.auth.views import LogoutView
from django.contrib import admin

# Fonction de redirection pour les anciennes URLs admin
def redirect_to_dashboard(request):
    return redirect('dashboard')

urlpatterns = [
    # Restaurer l'accès à l'interface d'administration Django
    path('admin/', admin.site.urls),
    path('dashboard-admin/', redirect_to_dashboard, name='dashboard_admin'),
    path('admin/logout/', LogoutView.as_view(next_page='register'), name='logout'),
    path('', include('library.urls')),
]

# Configuration explicite pour servir les fichiers médias en développement
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    print(f"Configuration des médias: URL={settings.MEDIA_URL}, ROOT={settings.MEDIA_ROOT}")
else:
    # En production, les fichiers médias devraient être servis par le serveur web
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
