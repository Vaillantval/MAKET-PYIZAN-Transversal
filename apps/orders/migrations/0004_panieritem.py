from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('orders', '0003_alter_commande_methode_paiement'),
        ('accounts', '0005_alter_customuser_role'),
        ('catalog', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='PanierItem',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('quantite', models.DecimalField(decimal_places=3, max_digits=10)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('produit', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='panier_items',
                    to='catalog.produit',
                )),
                ('user', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='panier_items',
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={
                'verbose_name': 'Article panier',
                'verbose_name_plural': 'Articles panier',
                'ordering': ['created_at'],
            },
        ),
        migrations.AddConstraint(
            model_name='panieritem',
            constraint=models.UniqueConstraint(fields=['user', 'produit'], name='unique_panier_user_produit'),
        ),
    ]
