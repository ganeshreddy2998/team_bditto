from django.db import models
from django.utils import timezone
from datetime import datetime
from django.template.defaultfilters import slugify

from samePinch.constants_formats import Constants
from accounts.models import Profile


class ReportIssue(models.Model):
    """
    ReportIssue, any Issue related to the application can be reported.
    """

    user_associated = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='userIssues')
    title = models.CharField(max_length=1500)
    description = models.TextField()
    status = models.CharField(max_length=250, choices=Constants.REPORT_ISSUE_STATUS, default='pending')
    reported_on = models.DateTimeField(default=timezone.now)
    slug = models.SlugField(blank=True, null=True)

    class Meta:
        verbose_name_plural = 'Report Issues'

    def __str__(self):
        return f'{self.title} - {self.user_associated.user.username}'

    def save(self, *args, **kwargs):
        self.slug = slugify( self.user_associated.user.username + '-' + str(self.reported_on) )
        super(ReportIssue,self).save(*args,**kwargs)