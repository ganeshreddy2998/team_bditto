# Generated by Django 2.2.10 on 2020-07-23 08:04

import datetime
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('friends', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='blockedusers',
            name='blocked_on',
            field=models.DateTimeField(default=datetime.datetime(2020, 7, 23, 13, 34, 38, 220728)),
        ),
        migrations.AlterField(
            model_name='friendrequest',
            name='sent_at',
            field=models.DateTimeField(default=datetime.datetime(2020, 7, 23, 13, 34, 38, 218741)),
        ),
        migrations.AlterField(
            model_name='reportusers',
            name='reported_on',
            field=models.DateTimeField(default=datetime.datetime(2020, 7, 23, 13, 34, 38, 220728)),
        ),
    ]
