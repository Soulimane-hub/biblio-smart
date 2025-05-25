from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from .models import Livre

class RegisterForm(UserCreationForm):
    email = forms.EmailField(required=True, label="Email")
    username = forms.CharField(max_length=150, required=True, label="Username")

    class Meta:
        model = User
        fields = ['username', 'email', 'password1']  # Supprimez password2

    def save(self, commit=True):
        user = super().save(commit=False)
        user.is_superuser = False  # Toujours définir is_superuser à False
        user.is_staff = False  # Facultatif : définir également is_staff à False
        if commit:
            user.save()
        return user

class LivreForm(forms.ModelForm):
    class Meta:
        model = Livre
        fields = ['titre', 'auteur', 'isbn', 'categorie', 'stock', 'prix', 'annee_publication']

class LivrePhotoForm(forms.ModelForm):
    class Meta:
        model = Livre
        fields = ['image', 'photo']
        widgets = {
            'image': forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
            'photo': forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
        }
        labels = {
            'image': 'Image principale',
            'photo': 'Photo secondaire',
        }
        help_texts = {
            'image': 'Image principale affichée sur la page de détails du livre',
            'photo': 'Photo supplémentaire du livre (couverture arrière, etc.)',
        }