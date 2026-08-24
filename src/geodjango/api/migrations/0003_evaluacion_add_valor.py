from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0002_alter_evaluacion_options'),
    ]

    operations = [
        migrations.AddField(
            model_name='evaluacion',
            name='valor',
            field=models.IntegerField(default=0),
        ),
    ]
