# Generated by Django 2.2.10 on 2020-07-25 10:58

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('friends', '0004_auto_20200725_1441'),
    ]

    operations = [
        migrations.AlterField(
            model_name='friendrequest',
            name='request_status',
            field=models.CharField(choices=[('pending', 'pending'), ('accepted', 'accepted'), ('blocked', 'blocked')], max_length=50),
        ),
    ]