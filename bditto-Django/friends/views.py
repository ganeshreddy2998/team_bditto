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
from django.db.models import Q

from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

import os
import requests

from samePinch import constants_formats as CustomFileFormats
from samePinch.permission import PartiallyBlockedPermission
from accounts.models import User, Profile
from .pagination_class import BlockedUserPagination
from .serializers import (BlockedUserSerializer, StatusSerializer, 
                            FriendRequestSerializer, StatusDetailSerializer,
                            NodeStatusSerializer, UserSerializer,FriendRequestNotifSerializer
                        )
from .models import FriendRequest, BlockedUsers, ReportUsers, Groups
from status.models import Status, Liked, Favourites
from status.serializers import ProfilesSerializer
#from notifications.models import Notifications
from miscellaneous.serializers import NotificationsSerializer
from notifications.models import Notification
from notifications.signals import notify

from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from django.views.decorators.vary import vary_on_cookie 

from time import sleep

from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
import json

from django.conf import settings
from django.core.cache.backends.base import DEFAULT_TIMEOUT
from django.core.cache import cache

CACHE_TTL = getattr(settings ,'CACHE_TTL' , DEFAULT_TIMEOUT)

def check_blocked_status(profile, logged_user_profile):
    """
    To check whether you are blocked by the user or user has blocked 
    you or neither of you are blocked.
    """

    blocked_status = ''
    you_blocked = BlockedUsers.objects.filter(blocked_by=logged_user_profile).filter(user_blocked=profile).first()
    he_blocked = BlockedUsers.objects.filter(user_blocked=logged_user_profile).filter(blocked_by=profile).first()
    if you_blocked:
        blocked_status = ['You have blocked the user.', 1]
    elif he_blocked:
        blocked_status = ['You are blocked by the user.', 2]

    return blocked_status

def check_request_status(profile, logged_user_profile):
    """
    To check whether a request is sent by either of the users or they,
    are already friends or no relation exists between them.
    """
    
    request_sent = FriendRequest.objects.filter(sender = logged_user_profile).filter(receiver = profile).first()
    request_received = FriendRequest.objects.filter(receiver = logged_user_profile).filter(sender = profile).first()
    request_status = ['NAF', 4]

    if request_sent:
        if request_sent.request_status == 'pending':
            request_status = ['You have already sent a request.', 1]
        elif request_sent.request_status == 'accepted':
            request_status = ['You are Already Friends.', 2]

    if request_received:
        if request_received.request_status == 'pending':
            request_status = ['You have already received a request.', 3]
        elif request_received.request_status == 'accepted':
            request_status = ['You are Already Friends.', 2]

    return request_status

class SendFriendRequest(APIView):
    """
    To send Friend request to a user.
    """

    permission_classes = (IsAuthenticated,PartiallyBlockedPermission)

    def post(self, request, *args, **kwargs):
        userId = request.data.get('userId')
        note = request.data.get('note')

        try:
            userId = int(userId)
            profile = get_object_or_404(Profile, pk=userId)
            user = profile.user

            logged_user = self.request.user

            if user.pk == logged_user.pk or profile is None:
                raise Http404

        except:
            response = {
                'message':'Invalid Request!!',
                'error':'Invalid UserId, No User Found',
                'status':HTTP_400_BAD_REQUEST
            }
            return Response(response, status=HTTP_400_BAD_REQUEST)
        
        logged_user_profile = logged_user.userAssociated.all().first()

        blocked_status = check_blocked_status(profile, logged_user_profile)
        if blocked_status:
            response = {
                'message':'Failed',
                'error':blocked_status[0],
                'status':HTTP_400_BAD_REQUEST
            }
            return Response(response, status=HTTP_400_BAD_REQUEST)

        request_status = check_request_status(profile, logged_user_profile)
        if request_status[0] != 'NAF':
            response = {
                'message':'Failed',
                'error':request_status[0],
                'status':HTTP_400_BAD_REQUEST
            }
            return Response(response, status=HTTP_400_BAD_REQUEST)

        try:
            friend_request = FriendRequest.objects.create(
                                                    sender = logged_user_profile, 
                                                    receiver = profile, 
                                                    note = note,
                                                    request_status = 'pending'
                                                )
            
            # add notification
            notif_content = "You have received a friend request from " + str(logged_user_profile.full_name)
            ids_assoc = "requestId:"+str(friend_request.pk)
            data=FriendRequestNotifSerializer(friend_request).data
            print(data)
            notify.send(user,
                        recipient=user,
                        description=notif_content,
                        verb='friend_request_sent',
                        data=data
                    )
            n=Notification.objects.filter(data={"data":data},recipient=user).order_by("-timestamp").first()
            d=NotificationsSerializer(n).data
            channel_layer = get_channel_layer()

            print(d,channel_layer.group_send)
            # Trigger message sent to group
            async_to_sync(channel_layer.group_send)(
                f"{user.id}", {
                                "type": "notifi",
                                "event": "friend_request_sent",
                                "data": str(d)})  
            
        except Exception as e:
            pass
        
        response = {
                'message':'success',
                'body':[],
                'status':HTTP_200_OK
            }
        return Response(response, status=HTTP_200_OK)

class ActionFriendRequest(APIView):
    """
    To change request status.
    """

    permission_classes = (IsAuthenticated,PartiallyBlockedPermission)

    def post(self, request, *args, **kwargs):
        requestId = request.data.get('requestId')
        action = request.data.get('action')

        user = self.request.user
        profile = user.userAssociated.all().first()

        try:
            requestId = int(requestId)
        except:
            response = {
                'message':'Failed',
                'error':'Invalid requestId.',
                'status':HTTP_400_BAD_REQUEST
            }
            return Response(response, status=HTTP_400_BAD_REQUEST)

        try:
            friend_request = get_object_or_404(FriendRequest, pk=requestId)
        except:
            response = {
                'message':'Failed',
                'error':'You might have either Deleted the request or Rejected the Request.',
                'status':HTTP_400_BAD_REQUEST
            }
            return Response(response, status=HTTP_400_BAD_REQUEST)

        if friend_request.request_status == 'accepted':
            response = {
                'message':'Failed',
                'error':'You have already accepted the request.',
                'status':HTTP_400_BAD_REQUEST
            }
            return Response(response, status=HTTP_400_BAD_REQUEST)

        if profile.pk == friend_request.sender.pk:
            if action == 'Delete':
                friend_request.delete()
                response = {
                    'message':'Request deleted Successfully.',
                    'body':[],
                    'status':HTTP_200_OK
                }
                return Response(response, status=HTTP_200_OK)
            response = {
                'message':'Failed',
                'error':'Invalid Request !!',
                'status':HTTP_400_BAD_REQUEST
            }
            return Response(response, status=HTTP_400_BAD_REQUEST)

        blocked_status = check_blocked_status(friend_request.sender, profile)
        if blocked_status:
            response = {
                'message':'Failed',
                'error':blocked_status[0],
                'status':HTTP_400_BAD_REQUEST
            }
            return Response(response, status=HTTP_400_BAD_REQUEST)
        
        if action == 'Accept':
            friend_request.request_status = 'accepted'
            friend_request.save()

            friend_id = []
            if profile.pk == friend_request.sender.pk:
                friend_id.append(friend_request.receiver.pk)
            
            if profile.pk == friend_request.receiver.pk:
                friend_id.append(friend_request.sender.pk)

            try:
                request_url = CustomFileFormats.NODE_SERVER_DOMAIN + 'user/friendship' 
                node_response = requests.post(
                    request_url,
                    headers={
                        'x-auth-server': CustomFileFormats.NODE_ADMIN_TOKEN,
                        'Content-Type':"application/json",
                    },
                    json={
                        'user': profile.pk,
                        'friends': friend_id,
                    }
                )

                node_response.raise_for_status()

            except Exception as e:
                response = {
                    'message':'Failed',
                    'error':str(e),
                    'status':HTTP_400_BAD_REQUEST
                }
                return Response(response, status=HTTP_400_BAD_REQUEST)
            
            try:
                # add notification
                notif_content = friend_request.receiver.full_name + " has accepted your friend request."
                ids_assoc = "requestId:"+str(friend_request.pk)
                data=FriendRequestNotifSerializer(friend_request).data
                notify.send(friend_request.sender.user,
                            recipient=friend_request.sender.user,
                            description=notif_content,
                            verb='friend_request_accepted',
                            data=data
                        )
                n=Notification.objects.filter(data={"data":data},recipient=user).order_by("-timestamp").first()
                d=NotificationsSerializer(n).data
                channel_layer = get_channel_layer()

                print(d,channel_layer.group_send)
                # Trigger message sent to group
                async_to_sync(channel_layer.group_send)(
                    f"{friend_request.sender.user.id}", {
                                    "type": "notifi",
                                    "event": "friend_request_accepted",
                                    "data": str(d)})  
                # Notifications.objects.create(
                #                     user_associated=friend_request.sender,
                #                     content=notif_content,
                #                     notification_type='friend_request_accepted',
                #                     associated_ids=ids_assoc
                #                 )
            except:
                pass

            response = {
                'message':'Success',
                'body':[],
                'status':HTTP_200_OK
            }
            return Response(response, status=HTTP_200_OK)

        elif action == 'Delete' or action == 'Reject':
            friend_request.delete()
            response = {
                'message':'Success',
                'body':[],
                'status':HTTP_200_OK
            }
            return Response(response, status=HTTP_200_OK)
        
        response = {
            'message':'Invalid Action !!',
            'error':'only Accept, Delete or Reject are allowed.',
            'status':HTTP_400_BAD_REQUEST
        }
        return Response(response, status=HTTP_400_BAD_REQUEST)

class UnFriendUser(APIView):
    """
    To unfriend a friend.
    """

    permission_classes = (IsAuthenticated,PartiallyBlockedPermission)

    def post(self, request, *args, **kwargs):
        userId = request.data.get('userId')
        logged_user = self.request.user

        try:
            userId = int(userId)
            profile = get_object_or_404(Profile, pk=userId)
            user = profile.user
            
            if user.pk == logged_user.pk:
                raise Http404

        except:
            response = {
                'message':'Invalid Request !!',
                'error':'Invalid userId',
                'status':HTTP_400_BAD_REQUEST
            }
            return Response(response, status=HTTP_400_BAD_REQUEST)

        try:
            logged_user_profile = logged_user.userAssociated.all().first()
            friend_request = FriendRequest.objects.filter(
                                                        Q(sender=profile, receiver=logged_user_profile)|
                                                        Q(sender=logged_user_profile, receiver=profile)).first()
            if not friend_request:
                raise Http404
        except:
            response = {
                'message':'Invalid Request !!',
                'error':'You are not Friends.',
                'status':HTTP_400_BAD_REQUEST
            }
            return Response(response, status=HTTP_400_BAD_REQUEST)

        friend_id = []
        if profile.pk == friend_request.sender.pk:
            friend_id.append(friend_request.receiver.pk)
        
        if profile.pk == friend_request.receiver.pk:
            friend_id.append(friend_request.sender.pk)

        try:
            request_url = CustomFileFormats.NODE_SERVER_DOMAIN + 'user/friendship' 
            node_response = requests.post(
                request_url,
                headers={
                    'x-auth-server': CustomFileFormats.NODE_ADMIN_TOKEN,
                    'Content-Type':"application/json",
                },
                json={
                    'user': profile.pk,
                    'friends': friend_id,
                }
            )

            node_response.raise_for_status()

        except Exception as e:
            response = {
                'message':'Failed',
                'error':str(e),
                'status':HTTP_400_BAD_REQUEST
            }
            return Response(response, status=HTTP_400_BAD_REQUEST)
            
        friend_request.delete()
        response = {
            'message':'Success',
            'body':[],
            'status':HTTP_200_OK
        }
        return Response(response, status=HTTP_200_OK)
        
class ToggleBlock(APIView):
    """
    Block an Unblocked user, Unblock an blocked user.
    """

    permission_classes = (IsAuthenticated,PartiallyBlockedPermission)

    def post(self, request, *args, **kwargs):
        userId = request.data.get('userId')
        logged_user = self.request.user

        try:
            userId = int(userId)
            profile = get_object_or_404(Profile, pk=userId)
            user = profile.user

            if user.pk == logged_user.pk:
                raise Http404

        except:
            response = {
                'message':'Invalid Request',
                'error':'Invalid UserId',
                'status':HTTP_400_BAD_REQUEST
            }
            return Response(response, status=HTTP_400_BAD_REQUEST)

        
        logged_user_profile = logged_user.userAssociated.all().first()
        check_blocked = BlockedUsers.objects.filter(blocked_by=profile).filter(user_blocked=logged_user_profile).first()
        if check_blocked:
            response = {
                'message':'Failed',
                'error':'You are already blocked by this user.',
                'status':HTTP_400_BAD_REQUEST
            }
            return Response(response, status=HTTP_400_BAD_REQUEST)

        friend_request = FriendRequest.objects.filter(
                                                        Q(sender=profile, receiver=logged_user_profile)|
                                                        Q(sender=logged_user_profile, receiver=profile)).first()
        check_blocked = BlockedUsers.objects.filter(blocked_by=logged_user_profile).filter(user_blocked=profile).first()

        if check_blocked:
            check_blocked.delete()

            # if friend_request:

            #     friend_id = []
            #     if profile.pk == friend_request.sender.pk:
            #         friend_id.append(friend_request.receiver.pk)
                
            #     if profile.pk == friend_request.receiver.pk:
            #         friend_id.append(friend_request.sender.pk)

            #     try:
            #         request_url = CustomFileFormats.NODE_SERVER_DOMAIN + 'user/friendship' 
            #         node_response = requests.post(
            #             request_url,
            #             headers={
            #                 'x-auth-server': CustomFileFormats.NODE_ADMIN_TOKEN,
            #                 'Content-Type':"application/json",
            #             },
            #             json={
            #                 'user': profile.pk,
            #                 'friends': friend_id,
            #             }
            #         )

            #         node_response.raise_for_status()

            #     except Exception as e:
            #         response = {
            #             'message':'Failed',
            #             'error':str(e),
            #             'status':HTTP_400_BAD_REQUEST
            #         }
            #         return Response(response, status=HTTP_400_BAD_REQUEST)


            #     friend_request.request_status = 'accepted'
            #     friend_request.save()

            message = 'User Unblocked'
            if friend_request:
                friend_request.delete()
        
        else:
            BlockedUsers.objects.create(blocked_by=logged_user_profile, user_blocked=profile)
            if friend_request:
                friend_id = []
                if profile.pk == friend_request.sender.pk:
                    friend_id.append(friend_request.receiver.pk)
                
                if profile.pk == friend_request.receiver.pk:
                    friend_id.append(friend_request.sender.pk)

                try:
                    request_url = CustomFileFormats.NODE_SERVER_DOMAIN + 'user/friendship' 
                    node_response = requests.post(
                        request_url,
                        headers={
                            'x-auth-server': CustomFileFormats.NODE_ADMIN_TOKEN,
                            'Content-Type':"application/json",
                        },
                        json={
                            'user': profile.pk,
                            'friends': friend_id,
                        }
                    )

                    node_response.raise_for_status()

                except Exception as e:
                    response = {
                        'message':'Failed',
                        'error':str(e),
                        'status':HTTP_400_BAD_REQUEST
                    }
                    return Response(response, status=HTTP_400_BAD_REQUEST)

                friend_request.request_status = 'blocked'
                friend_request.save()

            message='User Blocked'

        response = {
            'message': message,
            'body':[],
            'status':HTTP_200_OK
        }
        return Response(response, status=HTTP_200_OK)

class ReportUser(APIView):
    """
    Report a user.
    """

    permission_classes = (IsAuthenticated,PartiallyBlockedPermission)

    def post(self, request, *args, **kwargs):
        userId = request.data.get('userId')
        logged_user = self.request.user

        try:
            userId = int(userId)
            profile = get_object_or_404(Profile, pk=userId)
            user = profile.user

            if user.pk == logged_user.pk:
                raise Http404

        except:
            response = {
                'message':'Invalid Request',
                'error':'Invalid UserId',
                'status':HTTP_400_BAD_REQUEST
            }
            return Response(response, status=HTTP_400_BAD_REQUEST)
        
        logged_user_profile = logged_user.userAssociated.all().first()
        already_reported = ReportUsers.objects.filter(reported_by=logged_user_profile).filter(user_reported=profile).first()
        if already_reported:
            response = {
                'message':'Failed',
                'error':'Already reported this user.',
                'status':HTTP_400_BAD_REQUEST
            }
            return Response(response, status=HTTP_400_BAD_REQUEST)

        ReportUsers.objects.create(reported_by=logged_user_profile, user_reported=profile, status='pending')
        response = {
            'message':'Success',
            'body':[],
            'status':HTTP_200_OK
        }        
        return Response(response, status=HTTP_200_OK)
        
class GetBlockedUsers(APIView):
    """
    To get list of all the users whom you have blocked.
    """

    pagination_class = LimitOffsetPagination
    permission_classes = (IsAuthenticated,)

    
    def get(self, request, *args, **kwargs):

        user = self.request.user
        profile = user.userAssociated.all().first()
        blocked_users = BlockedUsers.objects.filter(blocked_by=profile)
        
        getblocked_id = "GetBlockedUsersBy_{}".format(user.id)
        if cache.get(getblocked_id):
            blocked_users = cache.get(getblocked_id)
        else:
            blocked_users = BlockedUsers.objects.filter(blocked_by=profile)
            cache.set(getblocked_id, blocked_users)

        if blocked_users:
            try:
                paginator = LimitOffsetPagination()
                paginated_list = paginator.paginate_queryset(blocked_users, request)
                data = BlockedUserSerializer(paginated_list, context={ 'request': request }, many=True).data

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
                data = BlockedUserSerializer(blocked_users, context={ 'request': request }, many=True).data

                response = {
                    'message':'success',
                    'body':data,
                    'status':HTTP_200_OK
                }
                return Response(response, status=HTTP_200_OK)

        response = {
            'message':'No Users blocked',
            'body':[],
            'status':HTTP_200_OK
        }
        return Response(response, status=HTTP_200_OK)

class ViewUserStatus(APIView):
    """
    used to get all status of a particular user.
    """

    permission_classes = (IsAuthenticated,)
    pagination_class = LimitOffsetPagination

    def post(self, request, *args, **kwargs):
        userId = request.data.get('userId')

        try:
            userId = int(userId)
            profile = get_object_or_404(Profile, pk=userId)
            user = profile.user

            if user.pk == self.request.user.pk:
                raise Http404
            
        except:
            response = {
                'message':'Invalid Request !!',
                'error':'Invalid userID',
                'status':HTTP_400_BAD_REQUEST
            }
            return Response(response, status=HTTP_400_BAD_REQUEST)

        if user.status != 'Activated':
            response = {
                'message':'Failed',
                'error':'user is not active',
                'status':HTTP_400_BAD_REQUEST
            }
            return Response(response, status=HTTP_400_BAD_REQUEST)

        logged_user = self.request.user
        logged_user_profile = logged_user.userAssociated.all().first()

        blocked_status = check_blocked_status(profile, logged_user_profile)

        if blocked_status:
            response = {
                'message':'No status Found',
                'error':blocked_status[0],
                'status':HTTP_400_BAD_REQUEST
            }
            return Response(response, status=HTTP_400_BAD_REQUEST)

        all_status = list(Status.objects.filter(author=profile).filter(Q(current_status='active')|Q(current_status='inactive')).order_by('-created_at'))

        if all_status:
            try:
                paginator = LimitOffsetPagination()
                paginated_list = paginator.paginate_queryset(all_status, request)
                data = StatusSerializer(paginated_list, context={ 'request': request }, many=True).data
                print(data)

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
                data = StatusSerializer(all_status, context={ 'request': request }, many=True).data

                response = {
                    'message':'success',
                    'body':data,
                    'status':HTTP_200_OK
                }
                return Response(response, status=HTTP_200_OK)

        response = {
            'message':'No status Found',
            'body':[],
            'status':HTTP_200_OK
        }
        return Response(response, status=HTTP_200_OK)


class FriendRequestsView(APIView):
    """
    To fetch all the pending Friend Requests.
    """

    permission_classes = (IsAuthenticated,)
    pagination_class = LimitOffsetPagination

    def post(self, request, *args, **kwargs):
        user = self.request.user
        profile = user.userAssociated.all().first()
        
        friendrequests_id = "GetFriendRequests_{}".format(user.id)
        if cache.get(friendrequests_id):
            pending_requests = cache.get(friendrequests_id)
        else:
            pending_requests = FriendRequest.objects.filter(receiver=profile).filter(request_status='pending')
            cache.set(friendrequests_id, pending_requests)

        if pending_requests:
            try:
                paginator = LimitOffsetPagination()
                paginated_list = paginator.paginate_queryset(pending_requests, request)
                data = FriendRequestSerializer(paginated_list, context={ 'request': request }, many=True).data

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
                data = FriendRequestSerializer(pending_requests, context={ 'request': request }, many=True).data

                response = {
                    'message':'success',
                    'body':data,
                    'status':HTTP_200_OK
                }
                return Response(response, status=HTTP_200_OK)

        response = {
            'message':'No pending requests',
            'body':[],
            'status':HTTP_200_OK
        }
        return Response(response, status=HTTP_200_OK)

class JoinLeaveGroup(APIView):
    """
    join/leave a group alternatively.
    NOTE:send to node server (Add admin token)
    """    

    def post(self, request, *args, **kwargs):
        admin_token = request.data.get('admin_token')
        userID = request.data.get('userID')

        try:
            profile = get_object_or_404(Profile, pk=int(userID))
            user = profile.user

            if profile is None:
                raise Http404
        except:
            response = {
                'message':'Failed',
                'error':'Invalid userID',
                'status':HTTP_400_BAD_REQUEST
            }
            return Response(response, status=HTTP_400_BAD_REQUEST)
        
        if admin_token != CustomFileFormats.DJANGO_ADMIN_TOKEN:
            response = {
                'message':'Invalid Request!!',
                'error':'send correct admin token.',
                'status':HTTP_400_BAD_REQUEST
            } 
            return Response(response, status=HTTP_400_BAD_REQUEST)

        status_id = request.data.get('statusID')
        try:
            status_id = int(status_id)
            status = get_object_or_404(Status, pk=status_id)
        except:
            response = {
                'message':'Invalid Request !!',
                'error':'Invalid statusId',
                'status':HTTP_400_BAD_REQUEST
            }
            return Response(response, status=HTTP_400_BAD_REQUEST)

        user_joined = Groups.objects.filter(participant=profile).filter(status_id=status).first()
        if user_joined:
            user_joined.joined = not user_joined.joined
            user_joined.save()
            participants = Groups.objects.filter(status_id=status_id,joined=True).exclude(participant=profile).values_list("participant__user")
            data={}
            #participants_profile = Groups.objects.filter(status_id=status).exclude(participant=profile).values_list("participant")
            participants_obj=User.objects.filter(id__in=participants)
            if user_joined.joined == True:
                text = 'A user has joined your group.'
                associated_ids = 'userID:' + str(profile.pk) + ' ' + 'groupID:' + str(status.pk)
                
                print(participants_obj)
                
                #participants_profile_obj=Profile.objects.filter(id__in=participants_profile)
                data['group'] = StatusSerializer(status).data
                data["user"]=UserSerializer(profile).data
                print(data)
                notify.send(user,
                            recipient=list(participants_obj),
                            description=text,
                            verb='group_joined',
                            data=data
                        )
            for user in participants_obj:
                n=Notification.objects.filter(data={"data":data},recipient=user).order_by("-timestamp").first()
                d=NotificationsSerializer(n).data
                try:
                    channel_layer = get_channel_layer()

                    print(d,channel_layer.group_send)
                    # Trigger message sent to group

                    async_to_sync(channel_layer.group_send)(
                        f"{user.id}", {
                                        "type": "notifi",
                                        "event": "group_joined",
                                        "data": str(d)})  
                except Exception as e:
                    print(str(e))
                #Notifications.objects.create(user_associated=profile, content=text, associated_ids=associated_ids, notification_type='group_joined')
        
        else:
            user_joined = Groups.objects.create(participant=profile,status_id=status)
            text = 'A user has joined your group.'
            associated_ids = 'userID:' + str(profile.pk) + ' ' + 'groupID:' + str(status.pk)
            participants = Groups.objects.filter(status_id=status).exclude(participant=profile).values_list("participant__user")

            participants_obj=User.objects.filter(id__in=participants)
            data={}
            #participants_profile_obj=Profile.objects.filter(id__in=participants_profile)
            data['group'] = StatusSerializer(status).data
            data["user"]=UserSerializer(profile).data
            print(data)
            notify.send(user,
                        recipient=list(participants_obj),
                        description=text,
                        verb='group_joined',
                        data=data
                    )
            for user in participants_obj:
                print(data)
                n=Notification.objects.filter(data={"data":data},recipient=user).order_by("-timestamp").first()
                print(n)
                d=NotificationsSerializer(n).data
                try:
                    channel_layer = get_channel_layer()

                    async_to_sync(channel_layer.group_send)(
                        f"{user.id}", {
                                        "type": "notifi",
                                        "event": "group_joined",
                                        "data": str(d)})  
                except Exception as e:
                    print(str(e))
            #Notifications.objects.create(user_associated=profile, content=text, associated_ids=associated_ids, notification_type='group_joined')
        
        response = {
            'message':'success',
            'body':{'joined_status':user_joined.joined},
            'status':HTTP_200_OK
        }
        return Response(response, status=HTTP_200_OK)

class GetGroupInfo(APIView):
    """
    get all the info related to a particular group
    """

    permission_classes = (IsAuthenticated,)

    def post(self, request, *args, **kwargs):
        user = self.request.user
        profile = user.userAssociated.all().first()

        statusId = request.data.get('statusId')
        try:
            statusId = int(statusId)
            status = get_object_or_404(Status, pk=statusId)
        except:
            response = {
                'message':"Invalid request !!",
                'error':'Invalid Status Id',
                'status':HTTP_400_BAD_REQUEST
            }
            return Response(response, status=HTTP_400_BAD_REQUEST)    

        data = StatusDetailSerializer(status).data

        is_liked = Liked.objects.filter(status=status).filter(liked_by=profile).first()
        if is_liked:
            data['isLiked'] = True
        else:
            data['isLiked'] = False

        is_favourite = Favourites.objects.filter(status=status).filter(set_by=profile).first()
        if is_favourite:
            data['isSaved'] = True
        else:
            data['isSaved'] = False

        is_member = Groups.objects.filter(status_id=status).filter(participant=profile).first()
        if is_member and is_member.joined:
            data['isMember'] = True
        else:
            data['isMember'] = False

        try:
            # group_active_users_request_url = CustomFileFormats.NODE_SERVER_DOMAIN + 'group/getActiveUsers/' 
            # group_active_users_node_response = requests.get(
            #     group_active_users_request_url,
            #     headers={'x-auth-server': CustomFileFormats.NODE_ADMIN_TOKEN},
            #     data={
            #         'statusID': status.pk,
            #     }
            # )

            # group_active_users_response = group_active_users_node_response.json()
            # active_users = group_active_users_response['activeUsers']

            # group_active_users_node_response.raise_for_status()

            all_members = list(Groups.objects.filter(status_id=status).filter(joined=True))
            profiles = ProfilesSerializer(all_members, many=True).data

            data['ActiveUsers'] = profiles
    
        except Exception as e:
            response = {
                'message':'Failed',
                'error':str(e),
                'status': HTTP_400_BAD_REQUEST
            }
            return Response(response, status=HTTP_400_BAD_REQUEST)

        response = {
            'message':'success',
            'body':data,
            'status':HTTP_200_OK
        }
        return Response(response, status=HTTP_200_OK)
        
class NodeGetGroupInfo(APIView):
    """
    used by node server to fetch info about groups.
    """

    def post(self, request, *args, **kwargs):
        admin_token = request.data['admin_token']
        try:
            group_ids = request.data.getlist('groupID')
        except:
            group_ids = request.data.get('groupID')
                
        if admin_token != CustomFileFormats.DJANGO_ADMIN_TOKEN:
            response = {
                'message':'Invalid Request!!',
                'error':'send correct admin token.',
                'status':HTTP_400_BAD_REQUEST
            } 
            return Response(response, status=HTTP_400_BAD_REQUEST)

        groups = []
        for i in group_ids:
            try:
                gId = int(i)
                group = get_object_or_404(Status, pk=gId)
                groups.append(group)
            except:
                response = {
                    'message':"Invalid Request",
                    "error":"Invalid GroupId",
                    "status":HTTP_400_BAD_REQUEST
                }
                return Response(response, status=HTTP_400_BAD_REQUEST)
        
        data = NodeStatusSerializer(groups, many=True).data
        response = {
            'message':'success',
            'body':data,
            'status':HTTP_200_OK
        }
        return Response(response, status=HTTP_200_OK)

class CheckFriendShip(APIView):
    """
    API for node server to checkfriendship btw users
    """

    def post(self, request, *args, **kwargs):
        admin_token = request.data['admin_token']
        userID1 = request.data.get('userID1')
        userID2 = request.data.get('userID2')
        
        if admin_token != CustomFileFormats.DJANGO_ADMIN_TOKEN:
            response = {
                'message':'Invalid Request!!',
                'error':'send correct admin token.',
                'status':HTTP_400_BAD_REQUEST
            } 
            return Response(response, status=HTTP_400_BAD_REQUEST)

        try:
            userID1 = int(userID1)
            userID2 = int(userID2)
            user1 = get_object_or_404(Profile, pk=userID1)
            user2 = get_object_or_404(Profile, pk=userID2)
        except:
            response = {
                'message':'Invalid Request!!',
                'error':'Invalid userID',
                'status':HTTP_400_BAD_REQUEST
            }
            return Response(response, status=HTTP_400_BAD_REQUEST)

        st = False
        check_status = check_request_status(user1, user2)
        if check_status[1] == 2:
            st = True
        
        response = {
            'message':'Success',
            'body':{'friends':st},
            'status':HTTP_200_OK
        }
        return Response(response, status=HTTP_200_OK)
            