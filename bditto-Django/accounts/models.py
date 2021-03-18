from django.db import models
from django.contrib.auth.base_user import BaseUserManager, AbstractBaseUser
from django.contrib.auth.models import PermissionsMixin
from django.utils import timezone
from django.db.models.signals import post_save
from django.contrib import messages
from django.core.mail import send_mail
from django.core.mail import EmailMessage
from django.template.loader import render_to_string
from django.template.defaultfilters import slugify

from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver
from rest_framework.authtoken.models import Token
import requests

from samePinch.constants_formats import Constants, NODE_SERVER_DOMAIN, NODE_ADMIN_TOKEN

class UserManager(BaseUserManager):
    def create_user(self, email, username, password=None):
        """
        Creates and saves a User with the given email and password.
        """
        if not email:
            raise ValueError('Users must have an email address')

        user = self.model(username=username, email=self.normalize_email(email))
        user.set_password(password)

        user.save(using=self._db)

        return user

    def create_staffuser(self, email, username, password):
        """
        Creates and saves a staff user with the given email and password.
        """
        user = self.create_user(
            email,
            username,
            password=password,
        )
        user.is_staff = True
        user.save(using=self._db)
        return user

    def create_superuser(self, email, username, password):
        """
        Creates and saves a superuser with the given email and password.
        """
        user = self.create_user(
            email,
            username,
            password=password,
        )
        user.is_staff = True
        user.is_admin = True
        user.save(using=self._db)
        return user

AUTH_PROVIDERS = {'facebook': 'facebook', 'google': 'google',
                  'twitter': 'twitter', 'email': 'email'}


class User(PermissionsMixin,AbstractBaseUser):
    """
    Custom user model 
    """

    email = models.EmailField(
        verbose_name='email address',
        max_length=255,
        unique=True,
    )
    username = models.CharField(max_length=1500)

    # Store signup time
    signup_time = models.DateTimeField(auto_now_add=True,blank=True,null=True)

    # Permission fields
    is_active = models.BooleanField(default=True)
    is_verified = models.BooleanField(default=False) #using for social user
    is_staff = models.BooleanField(default=False) # a admin user; non super-user
    is_admin = models.BooleanField(default=False) # a superuser
    is_server_admin = models.BooleanField(default=False) #access for server admin panel
    status = models.CharField(max_length=50, default="Activated", choices=Constants.USER_STATUS)
    
    auth_provider = models.CharField(
        max_length=255, blank=False,
        null=False, default=AUTH_PROVIDERS.get('email'))

    # notice the absence of a "Password field", that's built in.
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username',] # Email & Password are required by default.


    def get_full_name(self):
        # The user is identified by their email address
        return self.email

    def get_short_name(self):
        # The user is identified by their email address
        return self.email

    def __str__(self):              # __unicode__ on Python 2
        return self.email

    def has_perm(self, perm, obj=None):
        "Does the user have a specific permission?"
        # Simplest possible answer: Yes, always
        return True

    def has_module_perms(self, app_label):
        "Does the user have permissions to view the app `app_label`?"
        # Simplest possible answer: Yes, always
        return True

    @property
    def if_staff(self):
        "Is the user a member of staff?"
        return self.is_staff

    @property
    def if_admin(self):
        "Is the user a admin member?"
        return self.is_admin

    @property
    def if_active(self):
        "Is the user active?"
        return self.is_active

    @property
    def if_server_admin(self):
        return self.is_server_admin
    
    @property
    def if_is_verified(self):
        return self.is_verified

    objects = UserManager()


class Profile(models.Model):
    """
    User Profile, linked to the User model.
    """

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="userAssociated")
    full_name = models.CharField(max_length=2000, blank=True, null=True)
    country = models.CharField(max_length=2000, blank=True, null=True)
    city = models.CharField(max_length=2000, blank=True, null=True)
    gender = models.CharField(max_length=25, blank=True, null=True, choices=Constants.GENDER)
    date_of_birth = models.DateTimeField(blank=True, null=True)
    avatar = models.ImageField(upload_to = 'Profiles/', blank=True, null=True)  # User Profile Picture
    slug = models.SlugField(blank=True, null=True)
    online = models.BooleanField(default=False) # to track whether user is online/offline 

    class Meta:
        verbose_name_plural = 'User Profiles'

    def __str__(self):
        return f'{self.full_name} - {self.user.email}' 

    def save(self, *args, **kwargs):
        self.slug = slugify( self.user.username + ' ' + self.user.email )
        super(Profile,self).save(*args,**kwargs)

    @property
    def age(self):
        return timezone.now().year - self.date_of_birth.year


# creates Token whenever a new user Registers
# creates Profile object after social login

@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_auth_token(sender, instance=None, created=False, **kwargs):
    if created:
        Token.objects.create(user=instance)
    
    if instance.is_active and not instance.is_staff:
        profile = Profile.objects.filter(user=instance).first()
        if profile is None:
            profile = Profile.objects.create(user=instance)

            try:
                request_url = NODE_SERVER_DOMAIN + 'user/' 
#                node_response = requests.post(
#                    request_url,
#                    headers={
#                        'x-auth-server': NODE_ADMIN_TOKEN,
#                        'Content-Type':"application/json",
#                    },
#                    json={
#                        'userID': profile.pk,
#                        'fullname': profile.full_name,
#                        'username': instance.username,
#                        'profileURL': ''
#                    }
#                )
#
#                node_response.raise_for_status()
            except Exception as e:
                print(e)
                instance.delete()
   



