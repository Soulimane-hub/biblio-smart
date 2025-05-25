@staff_member_required
def validate_return(request, emprunt_id):
    if request.method == 'POST':
        try:
            emprunt = get_object_or_404(Emprunt, id=emprunt_id)
            retour = RetourLivre.objects.filter(emprunt=emprunt, statut='en_attente').first()
            
            if not retour:
                return JsonResponse({
                    'success': False,
                    'error': 'Aucune demande de retour en attente pour cet emprunt.'
                })
            
            # Mettre à jour le statut de la demande de retour
            retour.statut = 'valide'
            retour.date_validation = timezone.now()
            retour.save()
            
            # Mettre à jour l'emprunt
            emprunt.est_retourne = True
            emprunt.date_retour = timezone.now()
            emprunt.save()
            
            # Mettre à jour le stock du livre
            emprunt.livre.stock += 1
            emprunt.livre.save()
            
            # Envoyer un email de confirmation
            send_mail(
                'Retour de livre validé',
                f'Le retour du livre {emprunt.livre.titre} a été validé.',
                'bibliotheque@example.com',
                [emprunt.lecteur.email],
                fail_silently=True,
            )
            
            return JsonResponse({
                'success': True
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            })
    
    return JsonResponse({
        'success': False,
        'error': 'Méthode non autorisée'
    })

@staff_member_required
def refuse_return(request, emprunt_id):
    if request.method == 'POST':
        try:
            emprunt = get_object_or_404(Emprunt, id=emprunt_id)
            retour = RetourLivre.objects.filter(emprunt=emprunt, statut='en_attente').first()
            
            if not retour:
                return JsonResponse({
                    'success': False,
                    'error': 'Aucune demande de retour en attente pour cet emprunt.'
                })
            
            # Mettre à jour le statut de la demande de retour
            retour.statut = 'refuse'
            retour.date_validation = timezone.now()
            retour.save()
            
            # Envoyer un email d'information
            send_mail(
                'Demande de retour refusée',
                f'Votre demande de retour pour le livre {emprunt.livre.titre} a été refusée.',
                'bibliotheque@example.com',
                [emprunt.lecteur.email],
                fail_silently=True,
            )
            
            return JsonResponse({
                'success': True
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            })
    
    return JsonResponse({
        'success': False,
        'error': 'Méthode non autorisée'
    })
