from rest_framework import status
from rest_framework.response import Response
from rest_framework.decorators import api_view
from rest_framework.views import APIView
from rest_framework.authtoken.models import Token
from rest_framework.status import HTTP_200_OK, HTTP_400_BAD_REQUEST
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.generics import ListAPIView,UpdateAPIView,DestroyAPIView,CreateAPIView,RetrieveAPIView
from rest_framework.pagination import LimitOffsetPagination

from django.contrib import messages
from django.core.mail import send_mail
from django.conf import settings
from django.contrib.auth import login, authenticate, logout
from django.contrib.sites.shortcuts import get_current_site
from django.shortcuts import get_object_or_404
from django.utils.encoding import force_bytes, force_text
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.template.loader import render_to_string
from django.core.mail import EmailMessage
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.contrib.auth.hashers import check_password
from django.http import Http404
from datetime import datetime
from django.utils.timezone import make_aware
from django.db.models import Q

from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

import os
import requests

from samePinch import constants_formats as CustomFileFormats
from samePinch.permission import PartiallyBlockedPermission
from .serializers import (
                        RegistrationSerializer, ForgotPasswordEmailSerializer, 
                        SetNewPasswordSerializer, ProfileSerializer, 
                        FriendModelSerializer
                    )

from .models import User,Profile
from .tokens import account_activation_token
from friends.models import FriendRequest, BlockedUsers

from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from django.views.decorators.vary import vary_on_cookie 

from django.conf import settings
from django.core.cache.backends.base import DEFAULT_TIMEOUT
from django.core.cache import cache

CACHE_TTL = getattr(settings ,'CACHE_TTL' , DEFAULT_TIMEOUT)

import time 
class MyProfileView(APIView):

    permission_classes=(IsAuthenticated,)

    def get(self, request, *args, **kwargs):
        user = self.request.user
        
        myprofile_id = "GetMyProfile_{}".format(user.id)
        if cache.get(myprofile_id):
            data = cache.get(myprofile_id)
        else:
            profile = user.userAssociated.all().first()
            data = ProfileSerializer(profile).data
            cache.set(myprofile_id, data)

        try:
            current_site = get_current_site(request)
            
            request_url = CustomFileFormats.NODE_SERVER_DOMAIN + 'user/score/' 
            node_response = requests.get(
                request_url,
                headers={
                    'x-auth-server': CustomFileFormats.NODE_ADMIN_TOKEN,
                    'Content-Type':"application/json",
                },
                json={
                    'userID': profile.pk,
                }
            )

            user_score_response = node_response.json()
            node_response.raise_for_status()

            data['userScore'] = user_score_response['score']

            response = {
                'message':'Success',
                'body':data,
                'status':HTTP_200_OK
            }
            return Response(response, status=HTTP_200_OK)
            
        except Exception as e:
        
            response = {
                'message':'Request Failed',
                'error':str(e),
                'status': HTTP_400_BAD_REQUEST
            }
            return Response(response, status=HTTP_400_BAD_REQUEST)

class EditProfile(APIView):
    permission_classes = (IsAuthenticated,PartiallyBlockedPermission)

    def post(self, request, *args, **kwargs):
        user = self.request.user
        profile = user.userAssociated.all().first()

        username = request.data.get('username')
        full_name = request.data.get('full_name')
        city = request.data.get('city')
        country = request.data.get('country')
        gender = request.data.get('gender')
        dob = request.data.get('dob')

        if user.status == 'Deactivated':
            response = {
                'message':'Profile update failed.',
                'error':'Account deactivated',
                'status':HTTP_400_BAD_REQUEST
            }
            return Response(response, status=HTTP_400_BAD_REQUEST)

        check_username = User.objects.filter(username__iexact=username).exclude(email=user.email).first()
        if check_username:
            response = {
                'message':'Profile update failed.',
                'error':'Username is not Available! Already taken.',
                'status':HTTP_400_BAD_REQUEST
            }
            return Response(response, status=HTTP_400_BAD_REQUEST)

        if len(username.strip().split(" "))>1:
            response = {
                'message':'SignUp failed !!',
                'error':'Username cannot contain spaces.',
                'status':HTTP_400_BAD_REQUEST
            }
            return Response(response, status=HTTP_400_BAD_REQUEST)

        if username == full_name:
            response = {
                'message':'Profile update failed',
                'error':'Username cannot be equal to fullname.',
                'status':HTTP_400_BAD_REQUEST
            }
            return Response(response, status=HTTP_400_BAD_REQUEST)
        
        if gender != 'Male' and gender != 'Female' and gender != 'Other':
            response = {
                'message':'Profile update failed',
                'error':'Invalid gender !!',
                'status':HTTP_400_BAD_REQUEST
            }
            return Response(response, status=HTTP_400_BAD_REQUEST)

        user.username = username
        profile.full_name = full_name
        profile.city = city
        profile.country = country
        profile.gender = gender
        user.save()

        if dob:
            dob = datetime.strptime(dob,'%Y-%m-%d')
            profile.date_of_birth = make_aware(dob)

        profile_pic = request.data.get('avatar')
        if profile_pic:
            allowed_file_formats = CustomFileFormats.ALLOWED_PROFILE_IMAGE_FORMATS

            stats = profile_pic.size
            file_format = profile_pic.content_type

            max_size = CustomFileFormats.MAX_PROFILE_IMAGE_SIZE

            if stats > max_size:
                response = {
                    'message':'Profile update failed.',
                    'error':'File size too large, max allowed file size is 10MB.',
                    'status':HTTP_400_BAD_REQUEST
                }
                return Response(response, status=HTTP_400_BAD_REQUEST)

            if file_format not in allowed_file_formats:
                response = {
                    'message':'Profile update failed.',
                    'error':'File type not supported.',
                    'status':HTTP_400_BAD_REQUEST
                }
                return Response(response, status=HTTP_400_BAD_REQUEST)

            profile.avatar.delete()
            profile_pic.name = str(profile.pk)
            profile.avatar = profile_pic

        profile.save()
        profile.refresh_from_db()

        data = ProfileSerializer(profile).data

        try:
            current_site = CustomFileFormats.DJANGO_SERVER_DOMAIN
            if profile.avatar:
                profile_url = str(current_site) + str(profile.avatar.url)
            else:
                profile_url = ''

            request_url = CustomFileFormats.NODE_SERVER_DOMAIN + 'user/' 
            node_response = requests.post(
                request_url,
                headers={
                    'x-auth-server': CustomFileFormats.NODE_ADMIN_TOKEN,
                    'Content-Type':"application/json",
                },
                json={
                    'userID': profile.pk,
                    'fullname': profile.full_name,
                    'username': user.username,
                    'profileURL': profile_url
                }
            )

            user_update_response = node_response.json()
            node_response.raise_for_status()

        except Exception as e:
            response = {
                'message':'Profile updation failed.',
                'error':str(e),
                'status': HTTP_400_BAD_REQUEST
            }
            return Response(response, status=HTTP_400_BAD_REQUEST)

        try:
            user_score_request_url = CustomFileFormats.NODE_SERVER_DOMAIN + 'user/score/' 
            user_score_node_response = requests.get(
                user_score_request_url,
                headers={
                    'x-auth-server': CustomFileFormats.NODE_ADMIN_TOKEN,
                    'Content-Type':"application/json",
                },
                json={
                    'userID': profile.pk,
                }
            )

            user_score_response = user_score_node_response.json()
            data['userScore'] = user_score_response['score']

            user_score_node_response.raise_for_status()

            response = {
                'message':'Profile Successfully updated.',
                'body':data,
                'status':HTTP_200_OK
            }
            return Response(response, status=HTTP_200_OK)
            
        except Exception as e:
            response = {
                'message':'Profile updation failed.',
                'error':str(e),
                'status': HTTP_400_BAD_REQUEST
            }
            return Response(response, status=HTTP_400_BAD_REQUEST)


class UserProfileView(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request, *args, **kwargs):
        userId = request.data.get('userId')
        logged_user = self.request.user
        logged_user_profile = logged_user.userAssociated.all().first()

        try:
            userId = int(userId)
            profile = get_object_or_404(Profile, pk = userId)
            user = profile.user

            if profile == logged_user_profile:
                raise Http404
            
        except:
            response = {
                'message':'Request Failed!!',
                'error':'Invalid UserID',
                'status':HTTP_400_BAD_REQUEST
            }
            return Response(response, status=HTTP_400_BAD_REQUEST)

        if user.status != 'Activated' and user.status != 'Deactivated':
            response = {
                'message':'Request Failed!!',
                'error':'User is blocked or deleted',
                'status':HTTP_400_BAD_REQUEST
            }
            return Response(response, status=HTTP_400_BAD_REQUEST)

        blocked_status = ''
        you_blocked = BlockedUsers.objects.filter(blocked_by=logged_user_profile).filter(user_blocked=profile).first()
        he_blocked = BlockedUsers.objects.filter(user_blocked=logged_user_profile).filter(blocked_by=profile).first()
        if you_blocked:
            blocked_status = 'You have blocked the user.'
        elif he_blocked:
            blocked_status = 'You are blocked by the user.'

        if blocked_status:
            response = {
                'message':"User doesn't exist.",
                'error':blocked_status,
                'status':HTTP_400_BAD_REQUEST
            }
            return Response(response, status=HTTP_400_BAD_REQUEST)

        data = ProfileSerializer(profile).data

        request_sent = FriendRequest.objects.filter(sender = logged_user_profile).filter(receiver = profile).first()
        request_received = FriendRequest.objects.filter(receiver = logged_user_profile).filter(sender = profile).first()
        request_status = 'NAF'

        if request_sent:
            if request_sent.request_status == 'pending':
                request_status = 'Requested'
            elif request_sent.request_status == 'accepted':
                request_status = 'Friends'

        if request_received:
            if request_received.request_status == 'pending':
                request_status = 'Request Received'
            elif request_received.request_status == 'accepted':
                request_status = 'Friends'
        
        data['friendship'] = request_status
        try:
            user_score_request_url = CustomFileFormats.NODE_SERVER_DOMAIN + 'user/score/' 
            user_score_node_response = requests.get(
                user_score_request_url,
                headers={
                    'x-auth-server': CustomFileFormats.NODE_ADMIN_TOKEN,
                    'Content-Type':"application/json",
                },
                json={
                    'userID': profile.pk,
                }
            )

            user_score_response = user_score_node_response.json()
            data['userScore'] = user_score_response['score']

            user_score_node_response.raise_for_status()

            response = {
                'message':'success',
                'body':data,
                'status':HTTP_200_OK
            }
            return Response(response, status=HTTP_200_OK)
            
        except Exception as e:
            response = {
                'message':'Profile fetching failed.',
                'error':str(e),
                'status': HTTP_400_BAD_REQUEST
            }
            return Response(response, status=HTTP_400_BAD_REQUEST)

class GetFriendList(APIView):
    """
    To fetch all the friends of the current logged in user.
    """

    permission_classes = (IsAuthenticated,)
    pagination_class = LimitOffsetPagination
    def get(self, request, *args, **kwargs):
        
        user = self.request.user
        profile = user.userAssociated.all().first()
        
        getfriends_id = "GetFriendList_{}".format(user.id)
        if cache.get(getfriends_id):
            friends_list = cache.get(getfriends_id)
            print("GetFriendlist from Cache")
        else:
            requests_sent_accepted = list(FriendRequest.objects.filter(sender=profile).filter(request_status='accepted'))
            requests_received_accepted = list(FriendRequest.objects.filter(receiver=profile).filter(request_status='accepted'))

            friends_list = []
            friends_list.extend(requests_sent_accepted)
            friends_list.extend(requests_received_accepted)
            
            cache.set(getfriends_id, friends_list)
            print("GetFriendlist from DB")

        if friends_list:
            try:
                paginator = LimitOffsetPagination()
                paginated_list = paginator.paginate_queryset(friends_list, request)
                data = FriendModelSerializer(paginated_list, context={ 'request': request }, many=True).data

                response = {
                    'message':'success',
                    'links': {
                        'next': paginator.get_next_link(),
                        'previous': paginator.get_previous_link()
                    },
                    'count': paginator.count,
                    'body':data,
                    'status':HTTP_200_OK
                }
                return Response(response, status=HTTP_200_OK)
            except:
                data = FriendModelSerializer(friends_list, context={ 'request': request }, many=True).data

                response = {
                    'message':'success',
                    'body':data,
                    'status':HTTP_200_OK
                }
                return Response(response, status=HTTP_200_OK)

        response = {
            'message':'No Friends yet',
            'body':[],
            'status':HTTP_200_OK
        }
        return Response(response, status=HTTP_200_OK)

        
class SearchFriend(APIView):
    """
    To search friend on username and full_name.
    """

    permission_classes = (IsAuthenticated,)
    pagination_class = LimitOffsetPagination

    def post(self, request, *args, **kwargs):
        user = self.request.user
        profile = user.userAssociated.all().first()

        search_field = request.data.get('searchString')
        
        if user.status == 'Activated' or user.status=='Deactivated':
            matched_sender = list(FriendRequest.objects.filter(request_status='accepted').filter(sender=profile).filter(
                Q(receiver__full_name__icontains = search_field)|Q(receiver__user__username__icontains = search_field)
            ))

            matched_receiver = list(FriendRequest.objects.filter(request_status='accepted').filter(receiver=profile).filter(
                Q(sender__full_name__icontains = search_field)|Q(sender__user__username__icontains = search_field)
            ))

            friends_list = []
            friends_list.extend(matched_receiver)
            friends_list.extend(matched_sender)

            if friends_list:
                try:
                    paginator = LimitOffsetPagination()
                    paginated_list = paginator.paginate_queryset(friends_list, request)
                    data = FriendModelSerializer(paginated_list, context={ 'request': request }, many=True).data

                    response = {
                        'message':'success',
                        'links': {
                            'next': paginator.get_next_link(),
                            'previous': paginator.get_previous_link()
                        },
                        'count': paginator.count,
                        'body':data,
                        'status':HTTP_200_OK
                    }
                    return Response(response, status=HTTP_200_OK)
                except:
                    data = FriendModelSerializer(friends_list, context={ 'request': request }, many=True).data
                    response = {
                        'message':'success',
                        'body':data,
                        'status':HTTP_200_OK
                    }
                    return Response(response, status=HTTP_200_OK)

            response = {
                'message':'Success',
                'error':'No Users Found',
                'status':HTTP_200_OK
            }
            return Response(response, status=HTTP_200_OK)
        
        response = {
            'message':'failed',
            'error':'You are blocked from searching anything',
            'status':HTTP_400_BAD_REQUEST
        }
        return Response(response, status=HTTP_400_BAD_REQUEST)
        
class ToggleOnline(APIView):
    """
    change status of a user online/offline.
    """

    permission_classes = (IsAuthenticated,)

    def post(self, request, *args, **kwargs):
        user = self.request.user
        profile = user.userAssociated.all().first()

        profile.online = not profile.online
        profile.save()

        status = "Offline"

        if profile.online:
            status = "Online"

        response = {
            'message':'Success, user is now ' + status,
            'body':[],
            'status':HTTP_200_OK
        }
        return Response(response, status=HTTP_200_OK)
