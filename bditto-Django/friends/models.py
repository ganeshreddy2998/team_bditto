from django.db import models
from django.utils import timezone
from datetime import datetime
from django.template.defaultfilters import slugify 

from samePinch.constants_formats import Constants
from status.models import Status
from accounts.models import Profile


class FriendRequest(models.Model):
    """
    FriendRequest, to store sender, reciever and status of the request.
    """

    sender = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='senderProfile')
    receiver = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='receiverProfile')
    note = models.CharField(max_length=2500, blank=True, null=True)
    request_status = models.CharField(max_length=50, choices=Constants.REQUEST_STATUS)
    sent_at = models.DateTimeField(default=timezone.now)
    
    class Meta:
        verbose_name_plural = 'Friend Requests'

    def __str__(self):
        return f'{self.sender.user.username} - {self.receiver.user.username} - {self.request_status}'

class BlockedUsers(models.Model):
    """
    BlockedUsers, users blocked by any user will automatically be removed from his friends list.
    """

    blocked_by = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name="blockedBy")
    user_blocked = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name="userBlocked")
    blocked_on = models.DateTimeField(default=timezone.now)

    class Meta:
        verbose_name_plural = 'Blocked Users'

    def __str__(self):
        return f'{self.blocked_by.user.username} - {self.user_blocked.user.username}'

class ReportUsers(models.Model):
    """
    ReportUsers, any Issue related to a user can be reported.
    """

    reported_by = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name="reportedBy")
    user_reported = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name="userReported")
    status = models.CharField(max_length=50, choices=Constants.REPORT_STATUS)
    reported_on = models.DateTimeField(default=timezone.now)
    slug = models.SlugField(blank=True, null=True)
    
    class Meta:
        verbose_name_plural = 'Report Users'

    def __str__(self):
        return f'{self.reported_by.user.username} - {self.user_reported.user.username}'
    
    def save(self, *args, **kwargs):
        self.slug = slugify( self.reported_by.user.username + '-' + str(self.reported_on) + '-' + self.user_reported.user.username )
        super(ReportUsers, self).save(*args, **kwargs)

class Groups(models.Model):
    """
    Groups, keep track of users who ever joined the group.
    """

    status_id = models.ForeignKey(Status, on_delete=models.CASCADE, related_name='statusGroup')
    participant = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='groupParticipants',null=True, blank=True)
    joined = models.BooleanField(default=True)
    created_on = models.DateTimeField(default=timezone.now)

    class Meta:
        verbose_name_plural = 'Status join Logs'

    def __str__(self):
        return f'{self.status_id.content} - {self.created_on}'