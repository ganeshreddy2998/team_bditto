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

from .models import Status, Hashtags, StatusFiles, Favourites, Liked
from friends.models import Groups
from accounts.models import Profile

class UserSerializer(serializers.ModelSerializer):
    avatar = serializers.SerializerMethodField()
    username = serializers.SerializerMethodField()

    class Meta:
        model = Profile
        fields = ['full_name', 'username', 'pk', 'avatar']

    def get_username(self, obj):
        return obj.user.username
    
    def get_avatar(self, obj):
        try:
            return obj.avatar.url
        except:
            return ''

class HashtagsSerializer(serializers.ModelSerializer):
    """
    Hashtags serializer.
    """

    class Meta:
        model = Hashtags
        fields = ['pk', 'name', 'count', 'created_at']

class StatusFilesSerializer(serializers.ModelSerializer):
    """
    serializer for files related to the status.
    """

    file = serializers.FileField()

    class Meta:
        model = StatusFiles
        fields = ['file', 'file_type']

class StatusSerializer(serializers.ModelSerializer):
    """
    serializer for status data.
    """

    author = serializers.SerializerMethodField()
    background_image = serializers.SerializerMethodField()
    userCount = serializers.SerializerMethodField()
    profiles = serializers.SerializerMethodField()
    total_likes = serializers.SerializerMethodField()

    class Meta:
        model = Status
        fields = [
                    'pk',
                    'author', 
                    'content', 
                    'background_color', 
                    'background_image', 
                    'created_at', 
                    'current_status', 
                    'userCount',
                    'profiles',
                    'total_likes'
                ]

    def get_author(self, obj):
        return UserSerializer(obj.author).data

    def get_hashtags(self, obj):
        return HashtagsSerializer(obj.hashtags, many=True).data
    
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
        
    def get_total_likes(self, obj):
        totallikes = obj.likedStatus.all().count()
        return totallikes

class BriefStatusSerializer(serializers.ModelSerializer):
    """
    serializer for status data.
    """

    background_image = serializers.SerializerMethodField()
    total_likes = serializers.SerializerMethodField()

    class Meta:
        model = Status
        fields = [
                    'pk',
                    'content', 
                    'background_color', 
                    'background_image', 
                    'created_at', 
                    'current_status', 
                    'total_likes'
                ]
    
    def get_background_image(self, obj):
        try:
            return obj.background_image.url
        except:
            return ''
        
    def get_total_likes(self, obj):
        totallikes = obj.likedStatus.all().count()
        return totallikes

class FavouriteSerializer(serializers.ModelSerializer):
    """
    serializer for favourite status. 
    """

    status = serializers.SerializerMethodField()

    class Meta:
        model = Favourites
        fields = ['status', 'set_at']

    def get_status(self, obj):
        return StatusSerializer(obj.status).data


class LikedSerializer(serializers.ModelSerializer):
    """
    serializer for Liked status. 
    """

    status = serializers.SerializerMethodField()
    total_likes = serializers.SerializerMethodField()
    
    class Meta:
        model = Liked
        fields = ['status', 'liked_at', 'total_likes']

    def get_status(self, obj):
        return StatusSerializer(obj.status).data
    
    def get_total_likes(self, obj):
        totallikes = obj.status.likedStatus.all().count()
        return totallikes


class notifyLikedSerializer(serializers.ModelSerializer):
    """
    serializer for Liked status. 
    """

    status = serializers.SerializerMethodField()
    liked_by = serializers.SerializerMethodField()

    class Meta:
        model = Liked
        fields = ['status', 'liked_by', 'liked_at']

    def get_status(self, obj):
        return StatusSerializer(obj.status).data

    def get_liked_by(self, obj):
        return UserSerializer(obj.liked_by).data

class GroupSerializer(serializers.ModelSerializer):
    """
    serializer for group. 
    """

    status = serializers.SerializerMethodField()
    total_likes = serializers.SerializerMethodField()

    class Meta:
        model = Groups
        fields = ['status', 'created_on', 'total_likes']

    def get_status(self, obj):
        return StatusSerializer(obj.status_id).data
    
    def get_total_likes(self, obj):
        totallikes = obj.status_id.likedStatus.all().count()
        return totallikes


class RightNowStatusSerializer(serializers.ModelSerializer):
    """
    only selected fields of status.
    """

    author = serializers.SerializerMethodField()
    background_image = serializers.SerializerMethodField()

    class Meta:
        model = Status
        fields = ['pk', 'author', 'content', 'current_status', 'background_color', 'background_image', 'created_at']

    def get_author(self, obj):
        return UserSerializer(obj.author).data

    def get_background_image(self, obj):
        try:
            return obj.background_image.url
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

class TrendingStatusSerializer(serializers.ModelSerializer):
    """
    serializer for status data.
    """

    background_image = serializers.SerializerMethodField()
    profileURL = serializers.SerializerMethodField()
    username = serializers.SerializerMethodField()
    userId = serializers.SerializerMethodField()
    userCount = serializers.SerializerMethodField()
    profiles = serializers.SerializerMethodField()
    total_likes = serializers.SerializerMethodField()

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
                    'total_likes'
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
        
    def get_total_likes(self, obj):
        totallikes = obj.likedStatus.all().count()
        return totallikes

class SerializeGroup(serializers.ModelSerializer):
    """
    serialize group for trending status
    """

    status = serializers.SerializerMethodField()

    class Meta:
        model = Groups
        fields = ['status']

    def get_status(self, obj):
        return TrendingStatusSerializer(obj.status_id).data