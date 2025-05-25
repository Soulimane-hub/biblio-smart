from django.shortcuts import get_object_or_404
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
import io
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from .models import Payment

@login_required
def download_receipt(request, paiement_id):
    """Génère un reçu PDF élégant et professionnel pour un paiement."""
    paiement = get_object_or_404(Payment, id=paiement_id, user=request.user)
    buffer = io.BytesIO()
    
    # Définir la taille de page et les marges
    width, height = A4
    p = canvas.Canvas(buffer, pagesize=A4)
    
    # Couleurs - Thème bibliothèque
    couleur_primaire = colors.HexColor('#5e4b3e')  # Brun foncé (comme la navbar)
    couleur_secondaire = colors.HexColor('#f5f1e8')  # Beige clair (comme le fond)
    couleur_texte = colors.HexColor('#2c2416')  # Brun très foncé (pour le texte)
    couleur_accent = colors.HexColor('#c9b18c')  # Doré (pour les accents)
    couleur_highlight = colors.HexColor('#8a7866')  # Brun moyen (pour les titres)
    
    # Dessiner l'arrière-plan du header avec un motif de papier ancien
    p.setFillColor(couleur_secondaire)
    p.rect(0, height - 150, width, 150, fill=1)
    
    # Ajouter un motif de papier ancien (lignes horizontales subtiles)
    p.setStrokeColor(colors.HexColor('#e0d8c0'))
    p.setLineWidth(0.5)
    for y_pos in range(int(height - 150), int(height), 10):
        p.line(0, y_pos, width, y_pos)
    
    # Dessiner une bordure décorative en haut
    p.setStrokeColor(couleur_accent)
    p.setLineWidth(3)
    p.line(0, height - 10, width, height - 10)
    
    # Dessiner l'en-tête
    y = height - 50
    p.setFillColor(couleur_primaire)
    p.setFont("Times-Bold", 28)
    p.drawCentredString(width/2, y, "REÇU DE PAIEMENT")
    y -= 20
    p.setFont("Times-Italic", 14)
    p.drawCentredString(width/2, y, f"N° {paiement.id} - {paiement.date.strftime('%d/%m/%Y %H:%M')}")
    
    # Logo et nom de la bibliothèque
    import os
    from django.conf import settings
    logo_path = os.path.join(settings.BASE_DIR, "library", "static", "library", "images", "image.png")
    try:
        p.drawImage(logo_path, 50, height - 110, width=60, height=60, mask='auto')
    except Exception:
        # Si l'image n'est pas trouvée, dessiner un placeholder
        p.setFillColor(couleur_accent)
        p.rect(50, height - 110, 60, 60, fill=1)
        p.setFillColor(couleur_primaire)
        p.setFont("Times-Bold", 24)
        p.drawCentredString(80, height - 80, "B")
    
    # Informations de la bibliothèque
    p.setFillColor(couleur_primaire)
    p.setFont("Times-Bold", 18)
    p.drawString(120, height - 80, "BiblioSmart")
    p.setFont("Times-Italic", 12)
    p.drawString(120, height - 100, "Votre bibliothèque intelligente")
    
    # Ligne de séparation décorative
    p.setStrokeColor(couleur_accent)
    p.setLineWidth(1)
    p.line(50, height - 130, width - 50, height - 130)
    
    # Fond décoratif pour le corps du document
    p.setFillColor(colors.white)
    p.rect(40, 100, width - 80, height - 250, fill=1)
    
    # Ajouter une bordure décorative autour du corps
    p.setStrokeColor(couleur_accent)
    p.setLineWidth(1.5)
    p.rect(40, 100, width - 80, height - 250, stroke=1, fill=0)
    
    # Section des informations client
    y = height - 180
    p.setFillColor(couleur_highlight)
    p.setFont("Times-Bold", 16)
    p.drawString(60, y, "INFORMATIONS CLIENT")
    
    # Ligne décorative sous le titre de section
    p.setStrokeColor(couleur_accent)
    p.setLineWidth(1)
    p.line(60, y - 10, 250, y - 10)
    y -= 30
    
    # Nom du lecteur
    lecteur_nom = paiement.user.get_full_name() or paiement.user.username
    p.setFillColor(couleur_texte)
    p.setFont("Times-Bold", 12)
    p.drawString(60, y, "Lecteur:")
    p.setFont("Times-Roman", 12)
    p.drawString(150, y, lecteur_nom)
    y -= 20
    
    # Email du lecteur
    p.setFont("Times-Bold", 12)
    p.drawString(60, y, "Email:")
    p.setFont("Times-Roman", 12)
    p.drawString(150, y, paiement.user.email)
    y -= 20
    
    # Date d'inscription
    p.setFont("Times-Bold", 12)
    p.drawString(60, y, "Date d'inscription:")
    p.setFont("Times-Roman", 12)
    p.drawString(150, y, paiement.user.date_joined.strftime('%d/%m/%Y'))
    y -= 40
    
    # Section des détails de paiement
    p.setFillColor(couleur_highlight)
    p.setFont("Times-Bold", 16)
    p.drawString(60, y, "DÉTAILS DU PAIEMENT")
    
    # Ligne décorative sous le titre de section
    p.setStrokeColor(couleur_accent)
    p.setLineWidth(1)
    p.line(60, y - 10, 250, y - 10)
    y -= 30
    
    # Référence
    p.setFillColor(couleur_texte)
    p.setFont("Times-Bold", 12)
    p.drawString(60, y, "Référence:")
    p.setFont("Times-Roman", 12)
    p.drawString(150, y, f"REF-{paiement.id}-{paiement.date.strftime('%Y%m%d')}")
    y -= 20
    
    # Date
    p.setFont("Times-Bold", 12)
    p.drawString(60, y, "Date:")
    p.setFont("Times-Roman", 12)
    p.drawString(150, y, paiement.date.strftime('%d/%m/%Y %H:%M'))
    y -= 20
    
    # Description
    p.setFont("Times-Bold", 12)
    p.drawString(60, y, "Description:")
    p.setFont("Times-Roman", 12)
    
    # Déterminer la description
    if paiement.description:
        description = paiement.description
    elif getattr(paiement, 'emprunt', None):
        description = 'Paiement pour emprunt de livre'
    elif getattr(paiement, 'reservation', None):
        description = 'Paiement pour réservation de livre'
    else:
        description = 'Paiement'
    
    p.drawString(150, y, description)
    y -= 40
    
    # Section des détails du livre
    p.setFillColor(couleur_highlight)
    p.setFont("Times-Bold", 16)
    p.drawString(60, y, "DÉTAILS DU LIVRE")
    
    # Ligne décorative sous le titre de section
    p.setStrokeColor(couleur_accent)
    p.setLineWidth(1)
    p.line(60, y - 10, 250, y - 10)
    y -= 30
    
    # Titre du livre
    titre_livre = None
    if hasattr(paiement, 'livre') and paiement.livre:
        titre_livre = paiement.livre.titre
    elif hasattr(paiement, 'emprunt') and paiement.emprunt and hasattr(paiement.emprunt, 'livre') and paiement.emprunt.livre:
        titre_livre = paiement.emprunt.livre.titre
    elif hasattr(paiement, 'reservation') and paiement.reservation and hasattr(paiement.reservation, 'livre') and paiement.reservation.livre:
        titre_livre = paiement.reservation.livre.titre
    
    if titre_livre:
        p.setFillColor(couleur_texte)
        p.setFont("Times-Bold", 12)
        p.drawString(60, y, "Titre:")
        p.setFont("Times-Roman", 12)
        # Limiter la longueur du titre si nécessaire
        if len(titre_livre) > 50:
            titre_livre = titre_livre[:47] + "..."
        p.drawString(150, y, titre_livre)
        y -= 20
    
    # ID du livre
    num_livre = None
    if hasattr(paiement, 'livre') and paiement.livre:
        num_livre = paiement.livre.id
    elif hasattr(paiement, 'emprunt') and paiement.emprunt and hasattr(paiement.emprunt, 'livre') and paiement.emprunt.livre:
        num_livre = paiement.emprunt.livre.id
    elif hasattr(paiement, 'reservation') and paiement.reservation and hasattr(paiement.reservation, 'livre') and paiement.reservation.livre:
        num_livre = paiement.reservation.livre.id
    
    if num_livre:
        p.setFont("Times-Bold", 12)
        p.drawString(60, y, "ID du livre:")
        p.setFont("Times-Roman", 12)
        p.drawString(150, y, str(num_livre))
        y -= 20
    
    # Auteur du livre si disponible
    auteur = None
    if hasattr(paiement, 'livre') and paiement.livre and hasattr(paiement.livre, 'auteur'):
        auteur = paiement.livre.auteur
    elif hasattr(paiement, 'emprunt') and paiement.emprunt and hasattr(paiement.emprunt, 'livre') and hasattr(paiement.emprunt.livre, 'auteur'):
        auteur = paiement.emprunt.livre.auteur
    elif hasattr(paiement, 'reservation') and paiement.reservation and hasattr(paiement.reservation, 'livre') and hasattr(paiement.reservation.livre, 'auteur'):
        auteur = paiement.reservation.livre.auteur
    
    if auteur:
        p.setFont("Times-Bold", 12)
        p.drawString(60, y, "Auteur:")
        p.setFont("Times-Roman", 12)
        p.drawString(150, y, auteur)
        y -= 40
    else:
        y -= 20
    
    # Dessiner un tableau pour le récapitulatif
    p.setFillColor(couleur_highlight)
    p.setFont("Times-Bold", 16)
    p.drawString(60, y, "RÉCAPITULATIF")
    
    # Ligne décorative sous le titre de section
    p.setStrokeColor(couleur_accent)
    p.setLineWidth(1)
    p.line(60, y - 10, 250, y - 10)
    y -= 30
    
    # En-têtes du tableau
    p.setFillColor(couleur_primaire)
    p.rect(60, y - 20, width - 120, 20, fill=1)
    p.setFillColor(colors.white)
    p.setFont("Times-Bold", 10)
    p.drawString(70, y - 15, "DESCRIPTION")
    p.drawString(300, y - 15, "QUANTITÉ")
    p.drawString(400, y - 15, "PRIX")
    p.drawString(480, y - 15, "TOTAL")
    y -= 20
    
    # Ligne du tableau
    p.setFillColor(couleur_secondaire)
    p.rect(60, y - 20, width - 120, 20, fill=1)
    p.setFillColor(couleur_texte)
    p.setFont("Times-Roman", 10)
    p.drawString(70, y - 15, description)
    p.drawString(300, y - 15, "1")
    p.drawString(400, y - 15, f"{paiement.amount} MAD")
    p.drawString(480, y - 15, f"{paiement.amount} MAD")
    y -= 40
    
    # Total
    p.setFillColor(couleur_accent)
    p.setFont("Times-Bold", 14)
    p.drawString(400, y, "TOTAL:")
    p.drawString(480, y, f"{paiement.amount} MAD")
    
    # Pied de page
    p.setFillColor(couleur_primaire)
    p.rect(0, 0, width, 50, fill=1)
    
    # Ajouter un motif de papier ancien au pied de page
    p.setStrokeColor(colors.HexColor('#8a7866'))
    p.setLineWidth(0.5)
    for y_pos in range(0, 50, 10):
        p.line(0, y_pos, width, y_pos)
    
    # Texte du pied de page
    p.setFillColor(colors.white)
    p.setFont("Times-Roman", 10)
    p.drawCentredString(width/2, 30, "BiblioSmart - Votre bibliothèque intelligente")
    p.drawCentredString(width/2, 15, "© 2025 Tous droits réservés")
    
    # Dessiner un code-barres stylisé (simulé)
    barcode_data = f"RECU-{paiement.id}-{paiement.date.strftime('%Y%m%d')}"
    
    # Position et dimensions du code-barres
    barcode_x = width - 150
    barcode_y = 70
    barcode_width = 100
    barcode_height = 40
    
    # Dessiner le fond du code-barres
    p.setFillColor(colors.white)
    p.rect(barcode_x, barcode_y, barcode_width, barcode_height, fill=1)
    
    # Dessiner une bordure décorative autour du code-barres
    p.setStrokeColor(couleur_accent)
    p.setLineWidth(1)
    p.rect(barcode_x, barcode_y, barcode_width, barcode_height, stroke=1, fill=0)
    
    # Dessiner les lignes du code-barres
    p.setFillColor(couleur_texte)
    bar_width = 2
    space = 1
    x = barcode_x + 5
    
    # Générer un motif de code-barres basé sur l'ID du paiement
    for i in range(20):
        if (paiement.id + i) % 3 == 0:
            # Barre plus haute
            p.rect(x, barcode_y + 5, bar_width, barcode_height - 10, fill=1)
        else:
            # Barre normale
            p.rect(x, barcode_y + 10, bar_width, barcode_height - 20, fill=1)
        x += bar_width + space
    
    # Ajouter le numéro sous le code-barres
    p.setFont("Times-Roman", 8)
    p.drawCentredString(barcode_x + barcode_width/2, barcode_y - 10, barcode_data)
    
    # Ajouter un tampon "PAYÉ"
    p.saveState()
    p.translate(width/2, height/2)
    p.rotate(45)
    p.setFillColor(colors.HexColor('#c9b18c80'))  # Couleur dorée semi-transparente
    p.setFont("Times-Bold", 80)
    p.drawCentredString(0, 0, "PAYÉ")
    p.restoreState()
    
    # Ajouter un message de validation
    p.setFillColor(couleur_texte)
    p.setFont("Times-Italic", 8)
    p.drawCentredString(width/2, 60, "Ce reçu est un document officiel. Veuillez le conserver pour toute réclamation.")
    
    # Finaliser le PDF
    p.showPage()
    p.save()
    buffer.seek(0)
    
    # Retourner la réponse HTTP avec le PDF
    response = HttpResponse(buffer, content_type='application/pdf')
    # Utiliser 'inline' au lieu de 'attachment' pour afficher dans le navigateur
    response['Content-Disposition'] = f'inline; filename="recu_paiement_{paiement.id}.pdf"'
    return response
