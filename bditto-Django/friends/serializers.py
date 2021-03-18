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

from .models import BlockedUsers, FriendRequest, Groups
from accounts.models import User, Profile
from status.models import Status
from status.serializers import HashtagsSerializer, StatusFilesSerializer
from samePinch import constants_formats as CustomFileFormats
import requests

class UserSerializer(serializers.ModelSerializer):
    avatar = serializers.SerializerMethodField()
    username = serializers.SerializerMethodField()
    userID = serializers.SerializerMethodField()

    class Meta:
        model = Profile
        fields = ['full_name', 'username', 'userID', 'avatar']

    def get_username(self, obj):
        return obj.user.username
    
    def get_userID(self, obj):
        return obj.pk

    def get_avatar(self, obj):
        try:
            return obj.avatar.url
        except:
            return ''

class BlockedUserSerializer(serializers.ModelSerializer):
    user = serializers.SerializerMethodField()

    class Meta:
        model = BlockedUsers
        fields = ['user', 'blocked_on']

    def get_user(self, obj):
        return UserSerializer(obj.user_blocked).data

class StatusSerializer(serializers.ModelSerializer):

    username = serializers.SerializerMethodField()
    userId = serializers.SerializerMethodField()
    avatar = serializers.SerializerMethodField()
    background_image = serializers.FileField()
    userCount = serializers.SerializerMethodField()
    profiles = serializers.SerializerMethodField()
    total_likes = serializers.SerializerMethodField()

    class Meta:
        model = Status
        fields = [
                    'pk', 'content', 'background_color', 
                    'background_image', 'created_at', 
                    'current_status', 'username', 'userId',
                    'avatar','userCount',
                    'profiles', 'total_likes'
                ]

    def get_username(self, obj):
        return obj.author.user.username

    def get_userId(self, obj):
        return obj.author.pk

    def get_avatar(self, obj):
        try:
            return obj.author.avatar.url
        except:
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
    
    def get_total_likes(self, obj):
        totallikes = obj.likedStatus.all().count()
        return totallikes

class FriendRequestSerializer(serializers.ModelSerializer):

    user = serializers.SerializerMethodField()
    requestId = serializers.SerializerMethodField()

    class Meta:
        model = FriendRequest
        fields = ['user', 'note', 'requestId', 'sent_at', 'request_status']

    def get_user(self, obj):
        user = self.context['request'].user
        profile = user.userAssociated.all().first()

        return UserSerializer(obj.sender).data

    def get_requestId(self, obj):
        return obj.pk


class FriendRequestNotifSerializer(serializers.ModelSerializer):
    """
    serializer for friend request.
    """

    sender = serializers.SerializerMethodField()
    receiver = serializers.SerializerMethodField()

    class Meta:
        model = FriendRequest
        fields = ['sender', 'sent_at', 'pk', 'receiver']

    def get_sender(self, obj):
        return UserSerializer(obj.sender).data
    
    def get_receiver(self, obj):
        return UserSerializer(obj.receiver).data

class StatusDetailSerializer(serializers.ModelSerializer):
    """
    serializer for status data.
    """

    author = serializers.SerializerMethodField()
    hashtags = serializers.SerializerMethodField()
    background_image = serializers.SerializerMethodField()
    otherDocs = serializers.SerializerMethodField()
    userCount = serializers.SerializerMethodField()
    members = serializers.SerializerMethodField()
    rating = serializers.SerializerMethodField()
    inactive = serializers.SerializerMethodField()
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
                    'hashtags',
                    'otherDocs',
                    'userCount',
                    'members',
                    'inactive',
                    'rating',
                    'total_likes'
                ]

    def get_author(self, obj):
        return UserSerializer(obj.author).data

    def get_hashtags(self, obj):
        return HashtagsSerializer(obj.hashtags, many=True).data

    def get_otherDocs(self, obj):
        all_files = obj.statusFiles.all()
        return StatusFilesSerializer(all_files, many=True).data
    
    def get_background_image(self, obj):
        try:
            return obj.background_image.url
        except:
            return ''

    def get_userCount(self, obj):
        return len(list(Groups.objects.filter(status_id=obj).filter(joined=True)))

    def get_members(self, obj):
        all_members = list(Groups.objects.filter(status_id=obj).filter(joined=True))
        return ProfilesSerializer(all_members, many=True).data
        
    def get_inactive(self, obj):
        inactive_members = list(Groups.objects.filter(status_id=obj).filter(joined=False))
        return ProfilesSerializer(inactive_members, many=True).data

    def get_rating(self, obj):
        try:
            request_url = CustomFileFormats.NODE_SERVER_DOMAIN + 'group/rating' 
            node_response = requests.get(
                request_url,
                headers={
                    'x-auth-server': CustomFileFormats.NODE_ADMIN_TOKEN,
                    'Content-Type':"application/json",
                },
                json={
                    'statusID': obj.pk,
                }
            )

            node_response.raise_for_status()
            user_score_response = node_response.json()
            return user_score_response['rating']

        except Exception as e:
            raise serializers.ValidationError(str(e))
            
    def get_total_likes(self, obj):
        totallikes = obj.likedStatus.all().count()
        return totallikes

class NodeStatusSerializer(serializers.ModelSerializer):
    """
    serializer for node server get group request
    """

    class Meta:
        model = Status
        fields = ['pk', 'content', 'current_status']

class ProfilesSerializer(serializers.ModelSerializer):
    """
    serializer for first three profiles
    """

    profileURL = serializers.SerializerMethodField()
    username = serializers.SerializerMethodField()
    userID = serializers.SerializerMethodField()
    onlineStatus = serializers.SerializerMethodField()
    full_name = serializers.SerializerMethodField()

    class Meta:
        model = Groups
        fields = ['userID','username','full_name','onlineStatus','profileURL']

    def get_profileURL(self, obj):
        try:
            return obj.participant.avatar.url
        except:
            return ''
    
    def get_username(self, obj):
        return obj.participant.user.username
    
    def get_userID(self, obj):
        return obj.participant.pk
    
    def get_full_name(self, obj):
        return obj.participant.full_name
    
    def get_onlineStatus(self, obj):
        return obj.participant.online
