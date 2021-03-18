from django.db import models
from django.utils import timezone
from django.utils.html import strip_tags
from django.template.defaultfilters import slugify

import datetime
import pytz
from samePinch.constants_formats import Constants
from accounts.models import Profile


class Hashtags(models.Model):
    """
    Hashtags, which will be linked to the Status card.
    """

    name = models.CharField(max_length=2500)
    count = models.IntegerField(default=0)
    country = models.CharField(max_length=30, blank=True, null=True)
    created_at = models.DateTimeField(default=timezone.now)
    last_updated_at = models.DateTimeField(default=timezone.now)

    class Meta:
        verbose_name_plural = 'Hashtags'

    def __str__(self):
        return f'#{self.name}'

    def save(self, *args, **kwargs):
        self.last_updated_at = datetime.datetime.now(pytz.utc)
        super(Hashtags, self).save(*args, **kwargs)

class Status(models.Model):
    """
    Status, user can create multiple status.
    """

    author = models.ForeignKey(Profile, on_delete=models.SET_NULL, related_name='userStatus', null=True)
    content = models.CharField(max_length=140)
    background_color = models.CharField(max_length=30)
    background_image = models.ImageField(upload_to = 'Status/background_images/', null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    last_updated_at = models.DateTimeField(default=timezone.now)
    current_status = models.CharField(max_length=50, choices=Constants.CURRENT_STATUS, default='active')
    hashtags = models.ManyToManyField(Hashtags, related_name='associatedHashtags', blank=True)
    slug = models.SlugField(blank=True, null=True)

    class Meta:
        verbose_name_plural = 'Status Cards'

    def __str__(self):
        return self.content_stripped

    @property
    def content_stripped(self): 
        return strip_tags(self.content)

    def save(self, *args, **kwargs):
        self.last_updated_at = datetime.datetime.now(pytz.utc)
        self.slug = slugify( self.author.user.username + '-' + str(self.created_at) )
        super(Status, self).save(*args, **kwargs)

def picture_upload_path(instance, filename):
    return f'Status/files/{instance.status.pk}/{filename}'

class StatusFiles(models.Model):
    """
    StatusFiles, files linked with the status.
    """

    status = models.ForeignKey(Status, on_delete=models.CASCADE, related_name='statusFiles')
    file = models.FileField(upload_to = picture_upload_path)
    file_type = models.CharField(max_length=150, blank=True, null=True)

    class Meta:
        verbose_name_plural = 'Status Associated Files'

    def __str__(self):
        return self.status_stripped

    @property
    def status_stripped(self): 
           return strip_tags(self.status.content)

class Favourites(models.Model):
    """
    Favourites, status saved as favourite by the user.
    """

    status = models.ForeignKey(Status, on_delete=models.CASCADE, related_name='favouriteStatus')
    set_by = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='favouriteSetBy')
    set_at = models.DateTimeField(default=timezone.now)

    class Meta:
        verbose_name_plural = 'Favourites'

    def __str__(self):
        return f'{self.status_stripped} - {self.set_by.user.username}'

    @property
    def status_stripped(self):
        return strip_tags(self.status.content)

class Liked(models.Model):
    """
    Liked, status liked by user.
    """

    status = models.ForeignKey(Status, on_delete=models.CASCADE, related_name='likedStatus')
    liked_by = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='likedBy')
    liked_at = models.DateTimeField(default=timezone.now)

    class Meta:
        verbose_name_plural = 'Liked Status'

    def __str__(self):
        return f'{self.status_stripped} - {self.liked_by.user.username}'

    @property
    def status_stripped(self):
        return strip_tags(self.status.content)