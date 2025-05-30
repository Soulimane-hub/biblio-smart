# Generated by Django 4.2.20 on 2025-05-23 19:56

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('library', '0025_reservation_date_disponibilite'),
    ]

    operations = [
        migrations.RenameField(
            model_name='emprunt',
            old_name='date_retour_effective',
            new_name='date_retour_reel',
        ),
        migrations.RenameField(
            model_name='emprunt',
            old_name='retour_demande',
            new_name='demande_retour',
        ),
        migrations.RenameField(
            model_name='emprunt',
            old_name='retour_valide',
            new_name='est_retourne',
        ),
        migrations.AddField(
            model_name='emprunt',
            name='date_demande_retour',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='livre',
            name='photo',
            field=models.ImageField(blank=True, null=True, upload_to='livres/photos/'),
        ),
        migrations.AlterField(
            model_name='livre',
            name='isbn',
            field=models.CharField(blank=True, max_length=13, null=True, unique=True),
        ),
    ]
