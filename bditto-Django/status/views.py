from rest_framework import status
from rest_framework.response import Response
from rest_framework.decorators import api_view
from rest_framework.views import APIView
from rest_framework.authtoken.models import Token
from rest_framework.status import HTTP_200_OK, HTTP_400_BAD_REQUEST, HTTP_401_UNAUTHORIZED
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.generics import ListAPIView,UpdateAPIView,DestroyAPIView,CreateAPIView,RetrieveAPIView
from rest_framework.pagination import LimitOffsetPagination

from django.contrib import messages
from django.core.mail import send_mail
from django.conf import settings
from django.shortcuts import get_object_or_404
from django.http import Http404
from django.db.models import Q
from django.db.models import Count
from datetime import datetime, timedelta, timezone

from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from django.views.decorators.vary import vary_on_cookie 

from collections import OrderedDict

from samePinch import constants_formats as CustomFileFormats
from samePinch.permission import PartiallyBlockedPermission
from .profanity_check_list import arrBad
from .models import Status, Hashtags, StatusFiles, Favourites, Liked
from .serializers import (StatusSerializer, FavouriteSerializer, notifyLikedSerializer, GroupSerializer, 
                            HashtagsSerializer, BriefStatusSerializer,LikedSerializer,
                            RightNowStatusSerializer, TrendingStatusSerializer
                        )
from friends.models import Groups
#from Notifications.models import Notifications
from miscellaneous.serializers import NotificationsSerializer
from notifications.models import Notification
from notifications.signals import notify

#from django.utils.decorators import method_decorator
#from django.views.decorators.vary import vary_on_cookie 



from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
import json

from friends.serializers import UserSerializer
import re
import math
import requests


from django.conf import settings
from django.core.cache.backends.base import DEFAULT_TIMEOUT
from django.views.decorators.cache import cache_page
from django.core.cache import cache


# Tensorflow for Suggestions

import tensorflow_hub as hub
from scipy.spatial.distance import cosine
from .suggestionModel import suggsModel


CACHE_TTL = getattr(settings ,'CACHE_TTL' , DEFAULT_TIMEOUT)


def removeDuplicates(S): 
    """
    remove consecutive duplicates for profanity check.
    """

    n = len(S)  
    S =list(S)
    if (n < 2) : 
        return
          
    j = 0
    for i in range(n):  
        if (S[j] != S[i]): 
            j += 1
            S[j] = S[i]  
    j += 1
    S = S[:j] 
    S = ''.join(S)
    return S 
    
def profanityFilter(text):
    """
    To check for Vulgar/ abusive/ unethical content.
    """

    result = ''
    check = True
    text = text.lower()
    for word in arrBad:
        result = re.search('.*'+word+'.*', text)
        if result:
            check = False
            return check  

    words = text.strip().split(" ")
    for word in words:
        if len(word)>3:
            txt = removeDuplicates(word)
            for profane in arrBad:
                result = re.search('.*'+profane+'.*', txt)
                if result:
                    check = False
                    return check 
                     

    return check  

class CreateHashtags(APIView):
    """
    will return Hashtag Id if it exists else will create it.
    """

    permission_classes = (IsAuthenticated,PartiallyBlockedPermission)

    def post(self, request, *args, **kwargs):
        hashtag = request.data.get('hashtag')
        user = self.request.user
        profile = user.userAssociated.all().first()

        if user.status == 'Deactivated':
            response = {
                'message':'Failed',
                'error':'You are partially blocked, you have read-only access.',
                'status':HTTP_400_BAD_REQUEST
            }
            return Response(response, status=HTTP_400_BAD_REQUEST)

        if len(hashtag) > 20 or len(hashtag.split(" ")) > 1:
            response = {
                'message':'Failed !!',
                'error':'Hashtag can be off max 20 chars and It cannot have a space in between.',
                'status':HTTP_400_BAD_REQUEST
            }
            return Response(response, status=HTTP_400_BAD_REQUEST)

        hashtag_present = Hashtags.objects.filter(name__iexact=hashtag).first()
        
        if hashtag_present:
            hashtag_id = hashtag_present.pk
        else:
            created_new = Hashtags.objects.create(name=hashtag, country=profile.country)
            hashtag_id = created_new.pk

        response = {
            'message':'Success',
            'body': {'Id':hashtag_id},
            'status':HTTP_200_OK
        }
        return Response(response, status=HTTP_200_OK)


class CreateStatus(APIView):
    """
    To create a new status with profanity check and check on number of groups joined.
    NOTE: check for number of groups already joined before creating a new status.
    """

    permission_classes = (IsAuthenticated,PartiallyBlockedPermission)

    def post(self, request, *args, **kwargs):
        user = self.request.user
        profile = user.userAssociated.all().first()

        if profile is None:
            response = {
                'message':'Failed',
                'error':'User does not exist',
                'status':HTTP_401_UNAUTHORIZED
            }
            return Response(response, status=HTTP_401_UNAUTHORIZED)

        content = request.data.get('content')
        backgroundColor = request.data.get('backgroundColor')
        backgroundImage = request.data.get('backgroundImage')
        hashtags = request.data.getlist('hashtags')

        files = request.data.getlist('files')

        if user.status == 'Deactivated':
            response = {
                'message':'Failed',
                'error':'You are partially blocked, you have read-only access.',
                'status':HTTP_400_BAD_REQUEST
            }
            return Response(response, status=HTTP_400_BAD_REQUEST)
        
        try:
            group_limit_request_url = CustomFileFormats.NODE_SERVER_DOMAIN + 'user/checkLimit/' 
            print(group_limit_request_url)
            group_limit_node_response = requests.get(
                group_limit_request_url,
                headers={
                    'x-auth-server': CustomFileFormats.NODE_ADMIN_TOKEN,
                    'Content-Type':"application/json",
                },
                json={
                    'userID': profile.pk,
                }
            )

            print(group_limit_node_response)
            group_limit_response = group_limit_node_response.json()
            limit_reached = group_limit_response['limitReached']

            print(limit_reached, group_limit_response)

            group_limit_node_response.raise_for_status()

            if limit_reached:
                response = {
                    'message':'Status Creation Failed',
                    'error': 'Sorry! You can create infinite status, but right now you have joined 10 Conversation. Leave anyone conversation to create & join this one.',
                    'status': HTTP_400_BAD_REQUEST
                }
                return Response(response, status=HTTP_400_BAD_REQUEST)

        except Exception as e:
            response = {
                'message':'Status creation failed. Node error.',
                'error':str(e),
                'status': HTTP_400_BAD_REQUEST
            }
            return Response(response, status=HTTP_400_BAD_REQUEST)

        valid_check = profanityFilter(content)

        if not valid_check: 
            response = {
                'message':'Failed',
                'error':'Sorry! Your status contains some vulgur / illegal/ inappropriate comment.',
                'status':HTTP_400_BAD_REQUEST
            }
            return Response(response, status=HTTP_400_BAD_REQUEST)

        if len(content) > 140:
            response = {
                'message':'Failed',
                'error':'Character limit exceeded, Status can have a max_length of 140 chars.',
                'status':HTTP_400_BAD_REQUEST
            }
            return Response(response, status=HTTP_400_BAD_REQUEST)    

        if len(backgroundColor) >30:
            response = {
                'message':'Failed',
                'error':'Enter valid hexcode.',
                'status':HTTP_400_BAD_REQUEST
            }
            return Response(response, status=HTTP_400_BAD_REQUEST)

        try:
            stats = backgroundImage.size
            file_format = backgroundImage.content_type
        except:
            stats = 0
            file_format = ''

        allowed_file_formats = CustomFileFormats.ALLOWED_PROFILE_IMAGE_FORMATS

        if file_format and file_format not in allowed_file_formats:
            response = {
                'message':'Failed',
                'error':'File format not supported, please upload an PNG/JPG/JPEG type image.',
                'status':HTTP_400_BAD_REQUEST
            }
            return Response(response, status=HTTP_400_BAD_REQUEST)  

        max_size = CustomFileFormats.MAX_PROFILE_IMAGE_SIZE
        max_file_size = CustomFileFormats.MAX_STATUS_FILE_SIZE

        if len(files) > CustomFileFormats.MAX_STATUS_FILES:
            response = {
                'message':'Failed !!',
                'error':'Maximum 5 files allowed',
                'status':HTTP_400_BAD_REQUEST
            }
            return Response(response, status=HTTP_400_BAD_REQUEST)

        for file in files:
            if file and file.size > max_file_size:
                response = {
                    'message':'Failed',
                    'error':'Each file can have a maximum size of 3 MB',
                    'status':HTTP_400_BAD_REQUEST
                }
                return Response(response, status=HTTP_400_BAD_REQUEST) 

        create_status = Status.objects.create(
                                                author=profile,
                                                content=content,
                                                background_color=backgroundColor,
                                                background_image=backgroundImage,
                                            )

        try:
            create_group_request_url = CustomFileFormats.NODE_SERVER_DOMAIN + 'group/createGroup/' 
            create_group_node_response = requests.post(
                create_group_request_url,
                headers={
                    'x-auth-server': CustomFileFormats.NODE_ADMIN_TOKEN,
                    'Content-Type':"application/json",
                },
                json={
                    'statusID': create_status.pk,
                    'statusText': create_status.content,
                    'country': profile.country,
                    'creatorID': profile.pk,
                }
            )

            create_group_response = create_group_node_response.json()
            create_group_node_response.raise_for_status()
            print(create_group_response)
        except Exception as e:
            create_status.delete()
            response = {
                'message':'Status creation failed.Node',
                'error':str(e),
                'status': HTTP_400_BAD_REQUEST
            }
            return Response(response, status=HTTP_400_BAD_REQUEST)

        group = Groups.objects.create(status_id = create_status, participant=profile)

        for i in hashtags:
            try:
                hashtag = get_object_or_404(Hashtags, pk=int(i))
                hashtag.count = int(hashtag.count) + 1
                hashtag.save()
                create_status.hashtags.add(hashtag)
            except:
                create_status.delete()
                response = {
                    'message':'Failed',
                    'error':'Invalid hashtag.',
                    'status':HTTP_400_BAD_REQUEST
                }
                return Response(response, status=HTTP_400_BAD_REQUEST)

        create_status.save()

        for file in files:
            StatusFiles.objects.create(
                status=create_status,
                file_type=file.content_type,
                file=file,
            )

        response = {
            'message':'Status created.',
            'body':[],
            'status':HTTP_200_OK
        }
        return Response(response, status=HTTP_200_OK)

class EditStatus(APIView):
    """
    Edit a status with profanity check and check on number of groups joined.
    """

    permission_classes = (IsAuthenticated,PartiallyBlockedPermission)

    def post(self, request, *args, **kwargs):
        statusId = request.data.get('statusId')
        content = request.data.get('content')
        backgroundColor = request.data.get('backgroundColor')
        backgroundImage = request.data.get('backgroundImage')
        hashtags = request.data.getlist('hashtags')

        try:
            files = request.data.getlist('files')
        except:
            files = request.data.get('files')

        user = self.request.user
        profile = user.userAssociated.all().first()

        try:
            statusId = int(statusId)
            edit_status = get_object_or_404(Status, pk=statusId)
        except:
            response = {
                'message':'Failed',
                'error':'Invalid statusId',
                'status':HTTP_400_BAD_REQUEST
            }
            return Response(response, status=HTTP_400_BAD_REQUEST)

        if edit_status.author.pk != profile.pk:
            response = {
                'message':'Failed',
                'error':'You are not the author of this status.',
                'status':HTTP_400_BAD_REQUEST
            }
            return Response(response, status=HTTP_400_BAD_REQUEST)

        if edit_status.current_status == 'deleted':
            response = {
                'message':'Failed',
                'error':'Status already deleted.',
                'status':HTTP_400_BAD_REQUEST
            }
            return Response(response, status=HTTP_400_BAD_REQUEST)

        if user.status == 'Deactivated':
            response = {
                'message':'Failed',
                'error':'You are partially blocked, you have read-only access.',
                'status':HTTP_400_BAD_REQUEST
            }
            return Response(response, status=HTTP_400_BAD_REQUEST)
        
        valid_check = profanityFilter(content)

        if not valid_check: 
            response = {
                'message':'Failed',
                'error':'Sorry! Your status contains some vulgur / illegal/ inappropriate comment.',
                'status':HTTP_400_BAD_REQUEST
            }
            return Response(response, status=HTTP_400_BAD_REQUEST)

        if len(content) > 140:
            response = {
                'message':'Failed',
                'error':'Character limit exceeded, Status can have a max_length of 140 chars.',
                'status':HTTP_400_BAD_REQUEST
            }
            return Response(response, status=HTTP_400_BAD_REQUEST)    

        if len(backgroundColor) >30:
            response = {
                'message':'Failed',
                'error':'Enter valid hexcode.',
                'status':HTTP_400_BAD_REQUEST
            }
            return Response(response, status=HTTP_400_BAD_REQUEST)

        try:
            stats = backgroundImage.size
            file_format = backgroundImage.content_type
        except:
            stats = 0
            file_format = None

        allowed_file_formats = CustomFileFormats.ALLOWED_PROFILE_IMAGE_FORMATS

        if file_format and file_format not in allowed_file_formats:
            response = {
                'message':'Failed',
                'error':'File format not supported, please upload an PNG/JPG/JPEG type image.',
                'status':HTTP_400_BAD_REQUEST
            }
            return Response(response, status=HTTP_400_BAD_REQUEST)  

        max_size = CustomFileFormats.MAX_PROFILE_IMAGE_SIZE
        max_file_size = CustomFileFormats.MAX_STATUS_FILE_SIZE

        total_files = len(list(edit_status.statusFiles.all()))
        if files and files[0]!='':
            total_files += len(files)
        

        if total_files  > CustomFileFormats.MAX_STATUS_FILES:
            response = {
                'message':'Failed !!'+str(total_files) + str(len(files)),
                'error':'Maximum 5 files allowed',
                'status':HTTP_400_BAD_REQUEST
            }
            return Response(response, status=HTTP_400_BAD_REQUEST)

        for file in files:
            if file and file.size > max_file_size:
                response = {
                    'message':'Failed',
                    'error':'Each file can have a maximum size of 3 MB',
                    'status':HTTP_400_BAD_REQUEST
                }
                return Response(response, status=HTTP_400_BAD_REQUEST) 

        
        profile = user.userAssociated.all().first()
        edit_status.content = content
        edit_status.background_color = backgroundColor

        if backgroundImage:
            edit_status.background_image.delete()
            edit_status.background_image = backgroundImage

        edit_status.save()

        previous_hashtags = list(edit_status.hashtags.all())

        for i in previous_hashtags:
            i.count = max(0,int(i.count) - 1)
            i.save()
            if i.pk not in hashtags:
                edit_status.hashtags.remove(i)

        edit_status.save()

        for i in hashtags:
            try:
                hashtag = get_object_or_404(Hashtags, pk=int(i))
                hashtag.count = int(hashtag.count) + 1
                hashtag.save()
                edit_status.hashtags.add(hashtag)
                edit_status.save()
            except:
                response = {
                    'message':'Failed',
                    'error':'Invalid hashtag.',
                    'status':HTTP_400_BAD_REQUEST
                }
                return Response(response, status=HTTP_400_BAD_REQUEST)

        edit_status.save()
        for file in files:
            if file:
                StatusFiles.objects.create(
                    status=edit_status,
                    file_type=file.content_type,
                    file=file,
                )
        try:
                edit_group_request_url = CustomFileFormats.NODE_SERVER_DOMAIN + 'group/updateGroup' 
                edit_group_node_response = requests.post(
                    edit_group_request_url,
                    headers={
                        'x-auth-server': CustomFileFormats.NODE_ADMIN_TOKEN,
                        'Content-Type':"application/json",
                    },
                    json={
                        'statusID': edit_status.pk,
                        'statusText': edit_status.content
                    }
                )

                edit_group_response = edit_group_node_response.json()
                edit_group_node_response.raise_for_status()
                print(edit_group_response)
                
        except Exception as e:
        
            response = {
                'message':'Status updation failed.Node',
                'error':str(e),
                'status': HTTP_400_BAD_REQUEST
            }
            return Response(response, status=HTTP_400_BAD_REQUEST)
        
        response = {
            'message':'Status edited successfully.',
            'body':[],
            'status':HTTP_200_OK
        }
        return Response(response, status=HTTP_200_OK)

class ChangeStatus(APIView):
    """
    Change active deactive status of a user.
    NOTE: check for number of groups already joined before activating a status.
    NOTE: owner will be removed from the group if he/she dactivates a user.
    """

    permission_classes = (IsAuthenticated,PartiallyBlockedPermission)

    def post(self, request, *args, **kwargs):
        statusId = request.data.get('statusId')

        user = self.request.user
        profile = user.userAssociated.all().first()

        if user.status == 'Deactivated':
            response = {
                'message':'Failed',
                'error':'You are partially blocked, you have read-only access.',
                'status':HTTP_400_BAD_REQUEST
            }
            return Response(response, status=HTTP_400_BAD_REQUEST)

        try:
            statusId = int(statusId)
            status = get_object_or_404(Status, pk=statusId)
        except:
            response = {
                'message':'Failed',
                'error':'Invalid statusId',
                'status':HTTP_400_BAD_REQUEST
            }
            return Response(response, status=HTTP_400_BAD_REQUEST)

        if status.author.pk != profile.pk:
            response = {
                'message':'UnAuthorized request',
                'error':'You are not the owner of this status.',
                'status':HTTP_400_BAD_REQUEST
            }
            return Response(response, status=HTTP_400_BAD_REQUEST)

        if status.current_status == 'deleted':
            response = {
                'message':'Failed',
                'error':'Status alreday deleted',
                'status':HTTP_400_BAD_REQUEST
            }
            return Response(response, status=HTTP_400_BAD_REQUEST)

        if status.current_status == 'active':
            try:
                leave_group_request_url = CustomFileFormats.NODE_SERVER_DOMAIN + 'group/leaveGroup/' 
                leave_group_node_response = requests.post(
                    leave_group_request_url,
                    headers={
                        'x-auth-server': CustomFileFormats.NODE_ADMIN_TOKEN,
                        'Content-Type':"application/json",
                    },
                    json={
                        'userID': profile.pk,
                        "statusID":status.pk,
                    }
                )

                leave_group_response = leave_group_node_response.json()

                leave_group_node_response.raise_for_status()

            except Exception as e:
                response = {
                    'message':'Status change failed.',
                    'error':str(e),
                    'status': HTTP_400_BAD_REQUEST
                }
                return Response(response, status=HTTP_400_BAD_REQUEST)

            status.current_status = 'inactive'
            status.save()
            response = {
                'message':'Success, status set as inactive.',
                'body':[],
                'status':HTTP_200_OK
            }
            return Response(response, status=HTTP_200_OK)

        if status.current_status == 'inactive':
            
            try:
                group_limit_request_url = CustomFileFormats.NODE_SERVER_DOMAIN + 'user/checkLimit/' 
                group_limit_node_response = requests.get(
                    group_limit_request_url,
                    headers={
                        'x-auth-server': CustomFileFormats.NODE_ADMIN_TOKEN,
                        'Content-Type':"application/json",
                    },
                    json={
                        'userID': profile.pk,
                    }
                )

                group_limit_response = group_limit_node_response.json()
                limit_reached = group_limit_response['limitReached']

                group_limit_node_response.raise_for_status()

                if limit_reached:
                    response = {
                        'message':'Status not activated.',
                        'error': 'Sorry! You can create infinite status, but right now you have joined 10 Conversation. Leave anyone conversation to create & join this one.',
                        'status': HTTP_400_BAD_REQUEST
                    }
                    return Response(response, status=HTTP_400_BAD_REQUEST)

            except Exception as e:
                response = {
                    'message':'Status activation failed.',
                    'error':str(e),
                    'status': HTTP_400_BAD_REQUEST
                }
                return Response(response, status=HTTP_400_BAD_REQUEST)

            try:
                join_group_request_url = CustomFileFormats.NODE_SERVER_DOMAIN + 'group/joinGroup/' 
                join_group_node_response = requests.post(
                    join_group_request_url,
                    headers={
                        'x-auth-server': CustomFileFormats.NODE_ADMIN_TOKEN,
                        'Content-Type':"application/json",
                    },
                    json={
                        'userID': profile.pk,
                        'statusID': status.pk,
                    }
                )

                join_group_response = join_group_node_response.json()
                print(join_group_response)
                join_group_node_response.raise_for_status()

            except Exception as e:
                response = {
                    'message':'Status change failed.',
                    'error':str(e),
                    'status': HTTP_400_BAD_REQUEST
                }
                return Response(response, status=HTTP_400_BAD_REQUEST)

            status.current_status = 'active'
            status.save()
            response = {
                'message':'Success, status set as active.',
                'body':[],
                'status':HTTP_200_OK
            }
            return Response(response, status=HTTP_200_OK)
            
class SetFavourite(APIView):
    """
    set any status as favourite.
    """

    permission_classes = (IsAuthenticated,PartiallyBlockedPermission)

    def post(self, request, *args, **kwargs):
        statusId = request.data.get('statusId')
        user = self.request.user

        if user.status == 'Deactivated':
            response = {
                'message':'Failed',
                'error':'You are partially blocked, you have read-only access.',
                'status':HTTP_400_BAD_REQUEST
            }
            return Response(response, status=HTTP_400_BAD_REQUEST)

        try:
            statusId = int(statusId)
            status = get_object_or_404(Status, pk=statusId)
        except:
            response = {
                'message':'Failed !!',
                'error':'Invalid statusId',
                'status':HTTP_400_BAD_REQUEST
            }
            return Response(response, status=HTTP_400_BAD_REQUEST)

        if status.current_status == 'deleted':
            response = {
                'message':'Failed !!',
                'error':'Status already deleted',
                'status':HTTP_400_BAD_REQUEST
            }
            return Response(response, status=HTTP_400_BAD_REQUEST)

        user = self.request.user
        profile = user.userAssociated.all().first()
        favourite_set = Favourites.objects.filter(status=status, set_by=profile).first()

        if favourite_set:
            favourite_set.delete()
            response = {
                'message':'Success, status deleted from favourites.',
                'body':[],
                'status':HTTP_200_OK
            }
            return Response(response, status=HTTP_200_OK)
        else:
            Favourites.objects.create(status=status, set_by=profile)
            response = {
                'message':'Success, status set as favourite.',
                'body':[],
                'status':HTTP_200_OK
            }
            return Response(response, status=HTTP_200_OK)
import time 
class GetMyFavourites(APIView):
    """
    get all favourite status.
    """

    permission_classes = (IsAuthenticated,)
    pagination_class = LimitOffsetPagination
    def get(self, request, *args, **kwargs):
        
        user = self.request.user
        profile = user.userAssociated.all().first()
        
        favorite_id = "GetMyFavourite_{}".format(user.id)
        print(favorite_id)
        if cache.get(favorite_id):
            print("GET MY FAVOURITES FROM CACHE")
            favourites = cache.get(favorite_id)
        else:
            print("GET MY FAVOURITES FROM DB")
            favourites = Favourites.objects.filter(set_by=profile).order_by('-set_at')
            cache.set(favorite_id, favourites)

        if favourites:
            try:
                paginator = LimitOffsetPagination()
                paginated_list = paginator.paginate_queryset(favourites, request)
                data = FavouriteSerializer(paginated_list, context={ 'request': request }, many=True).data

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
                data = FavouriteSerializer(favourites, context={ 'request': request }, many=True).data

                response = {
                    'message':'success',
                    'body':data,
                    'status':HTTP_200_OK
                }
                return Response(response, status=HTTP_200_OK)

        response = {
            'message':'No status set as Favourite.',
            'body':[],
            'status':HTTP_200_OK
        }
        return Response(response, status=HTTP_200_OK)

class LikeStatus(APIView):
    """
    Like/Unlike any status.
    """

    permission_classes = (IsAuthenticated,PartiallyBlockedPermission)

    def post(self, request, *args, **kwargs):
        statusId = request.data.get('statusId')
        user = self.request.user
        print(request.data)
        if user.status == 'Deactivated':
            response = {
                'message':'Failed',
                'error':'You are partially blocked, you have read-only access.',
                'status':HTTP_400_BAD_REQUEST
            }
            return Response(response, status=HTTP_400_BAD_REQUEST)

        try:
            statusId = int(statusId)
            status = get_object_or_404(Status, pk=statusId)
        except:
            response = {
                'message':'Failed !!',
                'error':'Invalid statusId',
                'status':HTTP_400_BAD_REQUEST
            }
            return Response(response, status=HTTP_400_BAD_REQUEST)

        if status.current_status == 'deleted':
            response = {
                'message':'Failed !!',
                'error':'Status already deleted',
                'status':HTTP_400_BAD_REQUEST
            }
            return Response(response, status=HTTP_400_BAD_REQUEST)

        user = self.request.user
        profile = user.userAssociated.all().first()
        liked_set = Liked.objects.filter(status=status, liked_by=profile).first()

        if liked_set:
            liked_set.delete()
            response = {
                'message':'Success, status unliked.',
                'body':[],
                'status':HTTP_200_OK
            }
            return Response(response, status=HTTP_200_OK)
        else:
            liked_obj = Liked.objects.create(status=status, liked_by=profile)

            # add notification
            notif_content = "Your status is liked by " + profile.full_name
            ids_assoc = "likedId:"+str(liked_obj.pk)
            
            data=notifyLikedSerializer(liked_obj).data
            
            notify.send(user,
                        recipient=status.author.user,
                        description=notif_content,
                        verb='like',
                        data=data
                    )
            n=Notification.objects.filter(data={"data":data},recipient=status.author.user).order_by("-timestamp").first()
            d=NotificationsSerializer(n).data
            try:
                channel_layer = get_channel_layer()

                # Trigger message sent to group
                async_to_sync(channel_layer.group_send)(
                    f"{status.author.user.id}", {
                                    "type": "notifi",
                                    "event": "like",
                                    "data": str(d)})  
            except Exception as e:
                print(e)
                pass
            # Notifications.objects.create(
            #                     user_associated=status.author,
            #                     content=notif_content,
            #                     notification_type='like',
            #                     associated_ids=ids_assoc
            #                 )

            response = {
                'message':'Success, status liked.',
                'body':[],
                'status':HTTP_200_OK
            }
            return Response(response, status=HTTP_200_OK)

class GetMyLikedStatus(APIView):
    """
    get all liked status.
    """

    permission_classes = (IsAuthenticated,)
    pagination_class = LimitOffsetPagination
    
    def get(self, request, *args, **kwargs):

        user = self.request.user
        profile = user.userAssociated.all().first()
        
        likedstatus_id = "GetMyLikedStatus_{}".format(user.id)
        if cache.get(likedstatus_id):
            print("from cache")
            liked_status = cache.get(likedstatus_id)
        else:
            liked_status = Liked.objects.filter(liked_by=profile).order_by('-liked_at')
            cache.set(likedstatus_id, liked_status)
            print("from db")

        if liked_status:
            try:
                paginator = LimitOffsetPagination()
                paginated_list = paginator.paginate_queryset(liked_status, request)
                data = LikedSerializer(paginated_list, context={ 'request': request }, many=True).data

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
                data = LikedSerializer(liked_status, context={ 'request': request }, many=True).data

                response = {
                    'message':'success',
                    'body':data,
                    'status':HTTP_200_OK
                }
                return Response(response, status=HTTP_200_OK)

        response = {
            'message':'No liked status.',
            'body':[],
            'status':HTTP_200_OK
        }
        return Response(response, status=HTTP_200_OK)

class ViewHistory(APIView):
    """
    To get all the status that user has ever joined.
    """

    permission_classes = (IsAuthenticated,)
    pagination_class = LimitOffsetPagination
    
    def get(self, request, *args, **kwargs):
        user = self.request.user
        profile = user.userAssociated.all().first()
        
        history_id = "ViewHistory_{}".format(user.id)
        print(history_id)
        if cache.get(history_id):
            print("GET HISTORY FROM CACHE")
            all_status = cache.get(history_id)
        else:
            print("GET MY HISTORY FROM DB")
            all_status = Groups.objects.filter(Q(status_id__current_status = 'active')|Q(status_id__current_status = 'inactive')).filter(participant=profile).exclude(status_id__author=profile).order_by('-created_on')
            cache.set(history_id, all_status)


        all_status = Groups.objects.filter(Q(status_id__current_status = 'active')|Q(status_id__current_status = 'inactive')).filter(participant=profile).exclude(status_id__author=profile).order_by('-created_on')
        
        if all_status:
            try:
                paginator = LimitOffsetPagination()
                paginated_list = paginator.paginate_queryset(all_status, request)
                data = GroupSerializer(paginated_list, context={ 'request': request }, many=True).data

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
                data = GroupSerializer(all_status, context={ 'request': request }, many=True).data

                response = {
                    'message':'success',
                    'body':data,
                    'status':HTTP_200_OK
                }
                return Response(response, status=HTTP_200_OK)

        response = {
            'message':'No status.',
            'body':[],
            'status':HTTP_200_OK
        }
        return Response(response, status=HTTP_200_OK)

class GetMyStatus(APIView):
    """
    search status by status (active/inactive/deleted)
    """

    permission_classes = (IsAuthenticated,)

    def post(self, request, *args, **kwargs):
        status_type = request.data.get('status')
        user = self.request.user
        profile = user.userAssociated.all().first()
        
        getmystatus_id = "GetMyStatus_{}".format(user.id)
        if cache.get(getmystatus_id):
            mystatus = cache.get(getmystatus_id)
        else:
            mystatus = Status.objects.filter(author=profile)
            cache.set(getmystatus_id, mystatus)

        if status_type != 'Active' and status_type != 'Deactive' and status_type != 'All' and status_type != 'Deleted':
            response = {
                'message':'Invalid Request',
                'error':'Invalid status(only Active, Deactive, Deleted and All are allowed)',
                'status':HTTP_400_BAD_REQUEST
            }
            return Response(response, status=HTTP_400_BAD_REQUEST)

        if status_type == 'All':
            status1 = mystatus.filter(Q(current_status='active') | Q(current_status="inactive")).order_by('-created_at')
            order = ['active', 'inactive']
            status = sorted(status1, key=lambda x: order.index(x.current_status))
            
        elif status_type == 'Active':
            status = mystatus.filter(current_status='active').order_by('-created_at')
        elif status_type == 'Deactive':
            status = mystatus.filter(current_status='inactive').order_by('-created_at')
        elif status_type == 'Deleted':
            status = mystatus.filter(current_status='deleted').order_by('-created_at')

        # data = BriefStatusSerializer(status, context={ 'request': request }, many=True).data

        # response = {
        #     'message':'success',
        #     'body':data,
        #     'status':HTTP_200_OK
        # }
#        return Response(response, status=HTTP_200_OK)
        if status:
            try:
                paginator = LimitOffsetPagination()
                paginated_list = paginator.paginate_queryset(status, request)
                data = BriefStatusSerializer(paginated_list, context={ 'request': request }, many=True).data

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
                data = BriefStatusSerializer(status, context={ 'request': request }, many=True).data

                response = {
                    'message':'success',
                    'body':data,
                    'status':HTTP_200_OK
                }
                return Response(response, status=HTTP_200_OK)

        response = {
            'message':'No status for this hashtag.',
            'body':[],
            'status':HTTP_200_OK
        }
        return Response(response, status=HTTP_200_OK)
        

class DeleteStatus(APIView):
    """
    Delete a status.
    NOTE:The owner will be left from the conversation automatically.
    """

    permission_classes = (IsAuthenticated, PartiallyBlockedPermission)

    def post(self, request, *args, **kwargs):
        user = self.request.user
        profile = user.userAssociated.all().first()

        if user.status == 'Deactivated':
            response = {
                'message':'Failed',
                'error':'You are partially blocked, you have read-only access.',
                'status':HTTP_400_BAD_REQUEST
            }
            return Response(response, status=HTTP_400_BAD_REQUEST)

        statusId = request.data.get('statusId')

        try:
            statusId = int(statusId)
            status = get_object_or_404(Status, pk=statusId)
        except:
            response = {
                'message':'Invalid Request',
                'error':'Invalid statusId',
                'status':HTTP_400_BAD_REQUEST
            }
            return Response(response, status=HTTP_400_BAD_REQUEST)

        if status.author.pk != profile.pk:
            response = {
                'message':'Failed',
                'error':'You are not the owner of this status.',
                'status':HTTP_400_BAD_REQUEST
            }
            return Response(response, status=HTTP_400_BAD_REQUEST)

        if status.current_status == 'deleted':
            response = {
                'message':'Failed',
                'error':'Status alredy deleted',
                'status':HTTP_400_BAD_REQUEST
            }
            return Response(response, status=HTTP_400_BAD_REQUEST)

        try:
            group_leave_request_url = CustomFileFormats.NODE_SERVER_DOMAIN + 'group/leaveGroup/' 
            group_leave_node_response = requests.post(
                group_leave_request_url,
                headers={
                    'x-auth-server': CustomFileFormats.NODE_ADMIN_TOKEN,
                    'Content-Type':"application/json",
                },
                json={
                    'userID': profile.pk,
                    'statusID':status.pk,
                }
            )

            group_leave_response = group_leave_node_response.json()

            group_leave_node_response.raise_for_status()

        except Exception as e:
            response = {
                'message':'Status deletion failed.',
                'error':str(e),
                'status': HTTP_400_BAD_REQUEST
            }
            return Response(response, status=HTTP_400_BAD_REQUEST)

        status.current_status = 'deleted'
        status.save()

        Liked.objects.filter(status=status).delete()
        Favourites.objects.filter(status=status).delete()

        response = {
            'message':'Success, status deleted.',
            'body':[],
            'status':HTTP_200_OK
        }
        return Response(response, status=HTTP_200_OK)

    
class GetStatusByHashtags(APIView):
    """
    get all the status that have used this hashtag.
    """

    permission_classes = (IsAuthenticated,)
    pagination_class = LimitOffsetPagination

    def post(self, request, *args, **kwargs):
        status_code = request.data.get('status')
        hashtagId = request.data.get('hashtagId')
        country = request.data.get('country')
        
        if status_code != 'Active' and status_code != 'Deactive':
            response = {
                'message':'Invalid Request !!',
                'error':'Invalid status',
                'status':HTTP_400_BAD_REQUEST
            }
            return Response(response, status=HTTP_400_BAD_REQUEST)

        try:
            hashtagId = int(hashtagId)
            hashtag = get_object_or_404(Hashtags, pk=hashtagId)
        except:
            response = {
                'message':'Invalid Request !!',
                'error':'Invalid hashtagId',
                'status':HTTP_400_BAD_REQUEST
            }
            return Response(response, status=HTTP_400_BAD_REQUEST)

        if status_code == 'Active':
            filtered_status = Status.objects.filter(current_status='active').filter(hashtags=hashtag).order_by('-last_updated_at')
        else:
            filtered_status = Status.objects.filter(current_status='inactive').filter(hashtags=hashtag).order_by('-last_updated_at')

        if country != 'global' and country != '':
            filtered_status = filtered_status.filter(author__country=country).order_by('-last_updated_at')

        if filtered_status:
            try:
                paginator = LimitOffsetPagination()
                paginated_list = paginator.paginate_queryset(filtered_status, request)
                data = StatusSerializer(paginated_list, context={ 'request': request }, many=True).data

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
                data = StatusSerializer(filtered_status, context={ 'request': request }, many=True).data

                response = {
                    'message':'success',
                    'body':data,
                    'status':HTTP_200_OK
                }
                return Response(response, status=HTTP_200_OK)

        response = {
            'message':'No status for this hashtag.',
            'body':[],
            'status':HTTP_200_OK
        }
        return Response(response, status=HTTP_200_OK)


class SearchHashtags(APIView):
    """
    saearch hashtags
    """

    permission_classes = (IsAuthenticated,)

    def post(self, request, *args, **kwargs):
        search_text = request.data.get('text')

        user = self.request.user
        profile = user.userAssociated.all().first()

        if user.status == 'Deactivated':
            response = {
                'message':'Failed',
                'error':'You are partially blocked, you have read-only access.',
                'status':HTTP_400_BAD_REQUEST
            }
            return Response(response, status=HTTP_400_BAD_REQUEST)
        
        hashtags = Hashtags.objects.filter(name__icontains=search_text).values('pk','name').order_by('name')
        
        serialized_data = HashtagsSerializer(hashtags, many=True).data
        response = {
            'message':'Success',
            'body':serialized_data,
            'status':HTTP_200_OK
        }
        return Response(response, status=HTTP_200_OK)


class ListRightNowStatus(APIView):
    """
    list of status ordered by timestamp.
    """

    permission_classes = (IsAuthenticated,)
    
    def get(self, request, *args, **kwargs):
        
        rightnow_id = "RightNowStatus_02"
        if cache.get(rightnow_id):
            print("DATA FROM CACHE")
            all_status = cache.get(rightnow_id)
        else:
            print("DATA FROM DB")
            all_status = Status.objects.filter(current_status='active').order_by('-last_updated_at')
            cache.set(rightnow_id, all_status)

        if all_status:
            try:
                paginator = LimitOffsetPagination()
                paginated_list = paginator.paginate_queryset(all_status, request)
                data = TrendingStatusSerializer(paginated_list, context={ 'request': request }, many=True).data

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
                data = TrendingStatusSerializer(all_status, context={ 'request': request }, many=True).data

                response = {
                    'message':'success',
                    'body':data,
                    'status':HTTP_200_OK
                }
                return Response(response, status=HTTP_200_OK)

        response = {
            'message':'No status available.',
            'body':[],
            'status':HTTP_200_OK
        }
        return Response(response, status=HTTP_200_OK)

class GetTopNHashtags(APIView):
    """
    get top n hashtags based on z-score for a country or globally.
    """        

    permission_classes = (IsAuthenticated, )

    def post(self, request, *args, **kwargs):
        country = request.data.get('country')
        limit = request.data.get('limit')

        hashtags = Hashtags.objects.all()

        if not country and country != 'global' and country != '':
            hashtags = hashtags.filter(country=country)

        z_scores = {}
        for hashtag in hashtags:
            grouped_hashtags = list(Status.objects.filter(hashtags=hashtag).values('created_at').order_by('created_at').annotate(count=Count('created_at')))

            if grouped_hashtags:
                date_today = datetime.now(timezone.utc)
                created_at = hashtag.created_at
                most_recent_used = grouped_hashtags[-1]['created_at']
                days_created_before = date_today-created_at
                days_created_before = int(days_created_before.days)

                not_used_days = days_created_before - len(grouped_hashtags)
                if days_created_before>0:
                    avg_trend = hashtag.count/(days_created_before)
                else:
                    avg_trend = hashtag.count

                std_deviation = sum(((int(c['count']) - avg_trend) ** 2) for c in grouped_hashtags)
                std_deviation += (((0-avg_trend)**2) * (not_used_days))

                if days_created_before>0:
                    standard_deviation = math.sqrt(abs(std_deviation) / (days_created_before))
                else:
                    standard_deviation = math.sqrt(abs(std_deviation))

                standard_deviation = -1*standard_deviation if std_deviation<0 else standard_deviation

                if most_recent_used-date_today == 0:
                    current_trend = grouped_hashtags[-1]['count']
                else:
                    current_trend=0

                standard_deviation = 1 if standard_deviation==0 else standard_deviation
                z_score = (current_trend-avg_trend)/standard_deviation
                z_scores[hashtag] = z_score
            

        sorted_hashtags = OrderedDict(sorted(z_scores.items(), key = lambda kv:kv[1], reverse=True))
        
        positive_hashtags = []
        for hashtag in sorted_hashtags:
            # if sorted_hashtags[hashtag]<0:
            #     break
            positive_hashtags.append(hashtag)
        
        top_n_hashtags = positive_hashtags[:int(limit)]
        data = HashtagsSerializer(top_n_hashtags, many=True).data

        response = {
            'message':'Success',
            'body':data,
            'status':HTTP_200_OK
        }
        return Response(response, status=HTTP_200_OK)

class GetTrendingStatus(APIView):
    """
    get trending status based on z-score for a country or globally.
    """        

    permission_classes = (IsAuthenticated, )
    pagination_class = LimitOffsetPagination
    
    def post(self, request, *args, **kwargs):
        country = request.data.get('country')
        limit = request.data.get('limit')
        
        gettrending_id = "GetTrendingStatus_02"
        if cache.get(gettrending_id):
            status = cache.get(gettrending_id)
        else:
            status = Status.objects.filter(current_status="active")
            if country and country != 'global' and country != '':
                status = status.filter(author__country=country)
            cache.set(gettrending_id, status)

        #print(status)
        z_scores = {}
        for stat in status:
            grouped_status = list(Groups.objects.filter(status_id=stat).values('created_on').order_by('created_on').annotate(count=Count('created_on')))
            
            times_used = len(grouped_status)
            if grouped_status:
                date_today = datetime.now(timezone.utc)
                created_at = stat.created_at
                most_recent_used = grouped_status[-1]['created_on']
                days_created_before = date_today-created_at
                days_created_before = int(days_created_before.days)

                not_used_days = days_created_before - len(grouped_status)

                if days_created_before:
                    avg_trend = times_used/(days_created_before)
                else:
                    avg_trend = times_used

                std_deviation = sum(((int(c['count']) - avg_trend) ** 2) for c in grouped_status)
                std_deviation += (((0-avg_trend)**2) * (not_used_days))

                print(std_deviation)
                if days_created_before != 0:
                    standard_deviation = math.sqrt(abs(std_deviation) / (days_created_before))
                else:
                    standard_deviation = math.sqrt(abs(std_deviation))

                standard_deviation = -1*standard_deviation if std_deviation<0 else standard_deviation

                if most_recent_used-date_today == 0:
                    current_trend = grouped_status[-1]['count']
                else:
                    current_trend=0

                if standard_deviation!=0:
                    z_score = (current_trend-avg_trend)/standard_deviation
                else:
                    z_score = current_trend-avg_trend

                z_scores[stat] = z_score

        sorted_status = OrderedDict(sorted(z_scores.items(), key = lambda kv:kv[1], reverse=True))
        
        positive_status = []
        for stat in sorted_status:
            # if sorted_status[stat]<0:
            #     break
            positive_status.append(stat)
        trending_status=positive_status[::]
        
        # try:
        #     trending_status = positive_status[:int(limit)]
        # except:
        #     trending_status = positive_status[::]

        # data = TrendingStatusSerializer(trending_status, many=True).data

        # response = {
        #     'message':'Success',
        #     'body':data,
        #     'status':HTTP_200_OK
        # }
        # return Response(response, status=HTTP_200_OK)
        if trending_status:
            try:
                paginator = LimitOffsetPagination()
                paginated_list = paginator.paginate_queryset(trending_status, request)
                data = TrendingStatusSerializer(trending_status, context={ 'request': request }, many=True).data

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
                data = TrendingStatusSerializer(trending_status, context={ 'request': request }, many=True).data

                response = {
                    'message':'success',
                    'body':data,
                    'status':HTTP_200_OK
                }
                return Response(response, status=HTTP_200_OK)

        response = {
            'message':'No status available.',
            'body':[],
            'status':HTTP_200_OK
        }
        return Response(response, status=HTTP_200_OK)

class GetBuzzingStatus(APIView):
    """
    API to get list of Buzzing groups.
    NOTE:API call from Node Server
    """

    permission_classes = (IsAuthenticated,)

    def post(self, request, *args, **kwargs):
        location = request.data.get('location') 

        try:
            get_buzzing_group_request_url = CustomFileFormats.NODE_SERVER_DOMAIN + 'group/getBuzzingGroups/' 
            get_buzzing_group_node_response = requests.get(
                get_buzzing_group_request_url,
                headers={
                    'x-auth-server': CustomFileFormats.NODE_ADMIN_TOKEN,
                    'Content-Type':"application/json",
                },
                json={
                    'country': country,
                    "N":limit,
                }
            )

            get_buzzing_group_response = get_buzzing_group_node_response.json()
            get_buzzing_group_node_response.raise_for_status()

            buzz_groups = get_buzzing_group_response['groups']
            buzz_status = []

            for i in range(len(buzz_groups)):
                try:
                    status_buzzing = get_object_or_404(Status, pk=int(buzz_groups[i]['statusID']), current_status="active") 
                    buzz_status.append(status_buzzing)
                except:
                    response = {
                        'message':'Invalid GroupID',
                        'error':'Invalid groupID sent from node server',
                        'status':HTTP_400_BAD_REQUEST
                    }
                    return Response(response, status=HTTP_400_BAD_REQUEST)

        except Exception as e:
            response = {
                'message':'Buzzing groups not fetched',
                'error':str(e),
                'status': HTTP_400_BAD_REQUEST
            }
            return Response(response, status=HTTP_400_BAD_REQUEST)

        data = TrendingStatusSerializer(buzz_status, many=True).data

        response = {
            'message':'Success',
            'body':data,
            'status':HTTP_200_OK
        }
        return Response(response, status=HTTP_200_OK)
    

class getSuggestions(APIView):
    
    permission_classes = (IsAuthenticated,)

    def post(self, request, *args, **kwargs):
    
        country = request.data.get('country')
        city = request.data.get('city')
        current_status = request.data.get('status')
        statusID = request.data.get('statusID')

        try:
            status = get_object_or_404(Status, pk=int(statusID))
        except:
            response = {
                'message':'Invalid Request',
                'error':'Invalid statusID',
                'status':HTTP_400_BAD_REQUEST
            }
            return Response(response, status=HTTP_400_BAD_REQUEST)
        

        user = self.request.user
        profile = user.userAssociated.all().first()

        all_status = Status.objects.select_related('author').filter(current_status=current_status).exclude(author=profile).order_by('-created_at')

        if country and country != '':
            all_status = all_status.filter(author__country=country)
        
        if city and city != '':
            all_status = all_status.filter(author__city=city)
        
        data_set = list(all_status)

        search_text = status.content

        suggestions_list = []

        strength_embed = suggsModel([search_text])

        for data in data_set:
            corpus_embed = suggsModel([data.content])
            similarity = 1 - cosine(corpus_embed, strength_embed)
            suggestions_list.append([data, similarity])

        suggestions_list.sort(key=lambda k:k[1], reverse=True)

        suggs_list = []
        for i in suggestions_list:
            if i[1]< CustomFileFormats.STATUS_MATCH_THRESHOLD:
                break
            suggs_list.append(i[0])
        

        # data_set = [
        #     "Travelling to himalayas for outdoor activities",
        #     "planning to travel to Himalayas for retreat",
        #     "Trekking and camping in Himalayas",
        #     "Attending a camping trip across ganges near himalayas",
        #     "Travelling to Rishikesh and then heading towards himalayas for trekking",
        #     "Travelling to himalayas for Skiing events",
        #     "Trekking and camping at Dehradun",
        #     "Himalayas is a holy place to visit",
        #     "Visiting himalayas to spend time in ashram for retreat",
        #     "Splendid view of evening harati at ganges near himalayas",
        #     "Himalayas is a must place to travel",
        # ]

        # search_text = "Travelling to Himalayas for trekking and camping across Ganges"
        # suggestions_list = []

        # for data in data_set:
        #     corpus_embed = model([data])
        #     strength_embed = model([search_text])
        #     similarity = 1 - cosine(corpus_embed, strength_embed)
        #     suggestions_list.append([data, similarity])

        # suggestions_list.sort(key=lambda k:(k[1], k[0]), reverse=True)

        # suggs_list = []
        # for i in suggestions_list:
        #     suggs_list.append(i[0])

        # suggs_list = all_status
        
        if suggs_list:
            try:
                paginator = LimitOffsetPagination()
                paginated_list = paginator.paginate_queryset(suggs_list, request)
                data = StatusSerializer(paginated_list, context={ 'request': request }, many=True).data

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
                data = StatusSerializer(suggs_list, context={ 'request': request }, many=True).data

                response = {
                    'message':'success',
                    'body':data,
                    'status':HTTP_200_OK
                }
                return Response(response, status=HTTP_200_OK)

        response = {
            'message':'No status available.',
            'body':[],
            'status':HTTP_200_OK
        }

        return Response(response, status=HTTP_200_OK)