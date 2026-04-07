from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0002_add_auth_images'),
    ]

    operations = [
        migrations.AddField(
            model_name='sitesettings',
            name='android_apk',
            field=models.FileField(
                blank=True,
                null=True,
                upload_to='android/',
                verbose_name='Application Android (.apk)',
                help_text="Fichier .apk de l'application Android. Affiché comme bannière de téléchargement sur le site.",
            ),
        ),
    ]
