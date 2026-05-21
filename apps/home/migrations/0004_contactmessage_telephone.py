from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('home', '0003_contactreponse'),
    ]

    operations = [
        migrations.AddField(
            model_name='contactmessage',
            name='telephone',
            field=models.CharField(blank=True, max_length=20),
        ),
    ]
