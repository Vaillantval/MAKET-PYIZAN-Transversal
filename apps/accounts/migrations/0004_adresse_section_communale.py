from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0003_add_adresse'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='adresse',
            name='ville',
        ),
        migrations.AddField(
            model_name='adresse',
            name='section_communale',
            field=models.CharField(blank=True, max_length=150, verbose_name='Section communale'),
        ),
    ]
