# Generated by Django 2.2.1 on 2019-06-18 17:30

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('incidents', '0012_auto_20190618_1629'),
    ]

    operations = [
        migrations.AlterField(
            model_name='incident',
            name='hasPendingSeverityChange',
            field=models.IntegerField(default=0),
        ),
        migrations.AlterField(
            model_name='incident',
            name='hasPendingStatusChange',
            field=models.IntegerField(default=0),
        ),
    ]
