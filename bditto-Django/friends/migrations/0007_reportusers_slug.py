# Generated by Django 2.2.10 on 2020-08-09 16:04

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('friends', '0006_auto_20200804_2205'),
    ]

    operations = [
        migrations.AddField(
            model_name='reportusers',
            name='slug',
            field=models.SlugField(blank=True, null=True),
        ),
    ]