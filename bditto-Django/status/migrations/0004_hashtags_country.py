# Generated by Django 2.2.10 on 2020-08-02 16:25

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('status', '0003_statusfiles_file_type'),
    ]

    operations = [
        migrations.AddField(
            model_name='hashtags',
            name='country',
            field=models.CharField(blank=True, max_length=30, null=True),
        ),
    ]