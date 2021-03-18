# Generated by Django 2.2.10 on 2020-07-23 08:04

import datetime
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('accounts', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='ReportUsers',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('status', models.CharField(choices=[('pending', 'pending'), ('resolved', 'resolved'), ('discarded', 'discarded')], max_length=50)),
                ('reported_on', models.DateTimeField(default=datetime.datetime(2020, 7, 23, 13, 34, 22, 810266))),
                ('reported_by', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='reportedBy', to='accounts.Profile')),
                ('user_reported', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='userReported', to='accounts.Profile')),
            ],
            options={
                'verbose_name_plural': 'Report Users',
            },
        ),
        migrations.CreateModel(
            name='FriendRequest',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('request_status', models.CharField(choices=[('pending', 'pending'), ('accepted', 'accepted'), ('rejected', 'rejected'), ('deleted', 'deleted')], max_length=50)),
                ('sent_at', models.DateTimeField(default=datetime.datetime(2020, 7, 23, 13, 34, 22, 808271))),
                ('receiver', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='receiverProfile', to='accounts.Profile')),
                ('sender', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='senderProfile', to='accounts.Profile')),
            ],
            options={
                'verbose_name_plural': 'Friend Requests',
            },
        ),
        migrations.CreateModel(
            name='Friend',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('user1', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='user1', to='accounts.Profile')),
                ('user2', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='user2', to='accounts.Profile')),
            ],
            options={
                'verbose_name_plural': 'Friends',
            },
        ),
        migrations.CreateModel(
            name='BlockedUsers',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('blocked_on', models.DateTimeField(default=datetime.datetime(2020, 7, 23, 13, 34, 22, 810266))),
                ('blocked_by', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='blockedBy', to='accounts.Profile')),
                ('user_blocked', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='userBlocked', to='accounts.Profile')),
            ],
            options={
                'verbose_name_plural': 'Blocked Users',
            },
        ),
    ]