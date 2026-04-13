# Generated migration — widens numero_commande to accommodate UUID-based format
# CMD-{year}-{uuid4} = 4 + 4 + 1 + 36 = 45 characters

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('orders', '0005_panier_lignepanier_delete_panieritem'),
    ]

    operations = [
        migrations.AlterField(
            model_name='commande',
            name='numero_commande',
            field=models.CharField(blank=True, max_length=45, unique=True),
        ),
    ]
