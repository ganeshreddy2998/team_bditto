from rest_framework import serializers
from rest_framework.exceptions import AuthenticationFailed
from django.contrib.sites.shortcuts import get_current_site
from django.core.mail import EmailMessage
from django.utils.encoding import force_bytes, force_text
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.template.loader import render_to_string
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse,Http404
from django.conf import settings
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.utils.encoding import smart_str, force_str, smart_bytes, DjangoUnicodeDecodeError
from django.utils.encoding import force_bytes, force_text
from django.contrib.auth.hashers import check_password

from status.models import Status, Hashtags, StatusFiles, Favourites, Liked
from accounts.models import Profile
from friends.models import Groups

from notifications.models import Notification
class NotificationsSerializer(serializers.ModelSerializer):

    seen = serializers.SerializerMethodField()
    metas = serializers.SerializerMethodField()
    notification_type=serializers.SerializerMethodField()
    content=serializers.SerializerMethodField()
    created_at=serializers.SerializerMethodField()
    class Meta:
        model = Notification
        fields = [
            "pk",
            "notification_type",
            "seen",
            "metas",
            "created_at",
            "content"
        ]
    def get_seen(self, obj):
        c= not obj.unread
        return c

    def get_notification_type(self, obj):
        return obj.verb

    def get_content(self, obj):
        return obj.description

    def get_created_at(self, obj):
        return obj.timestamp
    
    def get_metas(self, obj):
        return obj.data['data']
       




class SearchUserSerializer(serializers.ModelSerializer):
    """
    serializer for user data
    """

    username = serializers.SerializerMethodField()
    avatar = serializers.SerializerMethodField()
    totalPost = serializers.SerializerMethodField()

    class Meta:
        model = Profile
        fields = ['pk', 'full_name', 'username', 'avatar', 'totalPost']

    def get_username(self, obj):
        return obj.user.username
    
    def get_totalPost(self, obj):
        tps = len(list(Status.objects.filter(author=obj)))
        return tps
    
    def get_avatar(self, obj):
        try:
            return obj.avatar.url
        except:
            return ''

class ProfilesSerializer(serializers.ModelSerializer):
    """
    serializer for first three profiles
    """

    profileURL = serializers.SerializerMethodField()

    class Meta:
        model = Groups
        fields = ['profileURL']

    def get_profileURL(self, obj):
        try:
            return obj.participant.avatar.url
        except:
            return ''

class SearchStatusSerializer(serializers.ModelSerializer):
    """
    serializer for status data.
    """

    background_image = serializers.SerializerMethodField()
    profileURL = serializers.SerializerMethodField()
    username = serializers.SerializerMethodField()
    userId = serializers.SerializerMethodField()
    userCount = serializers.SerializerMethodField()
    profiles = serializers.SerializerMethodField()

    class Meta:
        model = Status
        fields = [
                    'pk',
                    'userId',
                    'username',
                    'profileURL', 
                    'content', 
                    'background_color', 
                    'background_image', 
                    'created_at', 
                    'current_status',
                    'userCount',
                    'profiles',
                ]

    def get_username(self, obj):
        return obj.author.user.username
    
    def get_userId(self, obj):
        return obj.author.pk
    
    def get_profileURL(self, obj):
        if obj.author.avatar:
            return obj.author.avatar.url
        return ''
    
    def get_userCount(self, obj):
        return len(list(Groups.objects.filter(status_id=obj).filter(joined=True)))

    def get_profiles(self, obj):
        all_members = list(Groups.objects.filter(status_id=obj).filter(joined=True))
        flt_mem = []
        cnt  = 0
        for i in all_members:
            if i.participant and i.participant.avatar:
                cnt += 1
                flt_mem.append(i)
            if cnt == 3:
                break
        return ProfilesSerializer(flt_mem, many=True).data
    
    def get_background_image(self, obj):
        try:
            return obj.background_image.url
        except:
            return ''
