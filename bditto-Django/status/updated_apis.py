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
from friends.serializers import (BlockedUserSerializer, StatusSerializer, 
                            FriendRequestSerializer, StatusDetailSerializer,
                            NodeStatusSerializer, UserSerializer,FriendRequestNotifSerializer
                        )
from friends.models import FriendRequest, BlockedUsers, ReportUsers, Groups
from status.models import Status, Liked, Favourites, Hashtags
from status.serializers import ProfilesSerializer
#from notifications.models import Notifications
from miscellaneous.serializers import NotificationsSerializer
from notifications.models import Notification
from notifications.signals import notify

from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from django.views.decorators.vary import vary_on_cookie 

from time import sleep
from django.db.models import Count
from datetime import datetime, timedelta, timezone
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
import json

from django.conf import settings
from django.core.cache.backends.base import DEFAULT_TIMEOUT
from django.core.cache import cache

from .serializers import *
from collections import OrderedDict

import math

from miscellaneous.serializers import *


# Tensorflow for Suggestions

import tensorflow_hub as hub
from scipy.spatial.distance import cosine
from .suggestionModel import suggsModel
import tensorflow as tf


CACHE_TTL = getattr(settings ,'CACHE_TTL' , DEFAULT_TIMEOUT)



class getSuggestionsV2(APIView):
    """
    get suggestions API using universal sentence encoder tensorflow.
    NOTE:used tensorflow model
    """

    permission_classes = (IsAuthenticated,)
    
    def post(self, request, *args, **kwargs):
        
        locations = request.data.get("location")
        status_code = request.data.get("status")
        
        try:
            status = get_object_or_404(Status, pk=int(request.data.get("statusID")))
        except:
            response = {
                'message':'Invalid Request',
                'error':'Invalid statusID',
                'status':HTTP_400_BAD_REQUEST
            }
            return Response(response, status=HTTP_400_BAD_REQUEST)
        
        user = self.request.user
        profile = user.userAssociated.all().first()

        all_status = []
        
        if status_code != 'Active' and status_code != 'Deactive':
            response = {
                'message':'Invalid Request !!',
                'error':'Invalid status',
                'status':HTTP_400_BAD_REQUEST
            }
            return Response(response, status=HTTP_400_BAD_REQUEST)
        
        getsuggestions_id = request.data
        
        if cache.get(getsuggestions_id):
            all_status = cache.get(getsuggestions_id)
            print("suggestions from cache")
        else:
        
            if status_code == "Active":
                status1 = Status.objects.select_related('author').filter(current_status="active").exclude(author=profile).order_by('-created_at')
            else:
                status1 = Status.objects.select_related('author').filter(current_status="inactive").exclude(author=profile).order_by('-created_at')

            for location in locations:


                if location["country"] != "" and location["city"] != []:
                    cities = list(map(lambda x:x.lower(), location["city"]))
                    all_status.extend(status1.filter(author__city__in = cities).order_by('-created_at'))

                elif location["country"] != "" and location["city"] == []:
                    all_status.extend(status1.filter(author__country = location["country"].lower()).order_by('-created_at')) 

                elif (location["country"] == "" and location["city"] == []) or (location["country"] == "" and location["city"] != []):
                          response = {
                            'message':"country can't be empty",
                            'status':HTTP_400_BAD_REQUEST
                          }
                          return Response(response, status=HTTP_400_BAD_REQUEST)
                        
            cache.set(getsuggestions_id, all_status)
            print("suggestions from DB")
                
                                                    
        data_set = all_status
        
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


                    
class GetStatusByHashtagsV2(APIView):
    """
    get all the status that have used this hashtag.
    """

    permission_classes = (IsAuthenticated,)
    pagination_class = LimitOffsetPagination

    def post(self, request, *args, **kwargs):
        
        status_code = request.data.get("status")
        location = request.data.get("location")
        hashtag_id = int(request.data.get("hashtagID"))
        
        getstatusbyhashtag_id = request.data    
        
        if status_code != 'Active' and status_code != 'Deactive':
            response = {
                'message':'Invalid Request !!',
                'error':'Invalid status',
                'status':HTTP_400_BAD_REQUEST
            }
            return Response(response, status=HTTP_400_BAD_REQUEST)

        try:
            hashtag = get_object_or_404(Hashtags, pk=hashtag_id)
        except Exception as e:
            print(hashtag_id, type(hashtag_id))
            response = {
                'message':'Invalid Request !!',
                'error':'Invalid hashtagId',
                'status':HTTP_400_BAD_REQUEST
            }
            return Response(response, status=HTTP_400_BAD_REQUEST)
        
        if cache.get(getstatusbyhashtag_id):
            filtered_status = cache.get(getstatusbyhashtag_id)
            print("statusbyhashtag from cache")
        else:
            countries = list(map(lambda x:x.lower(), location))
            if status_code == 'Active':
                filtered_status = Status.objects.filter(current_status='active', author__country__in=countries).filter(hashtags=hashtag).order_by('-last_updated_at')
            else:
                filtered_status = Status.objects.filter(current_status='inactive',author__country__in=countries).filter(hashtags=hashtag).order_by('-last_updated_at')
            cache.set(getstatusbyhashtag_id, filtered_status)
            print("statusbyhashtag from db")

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
                                                                                                                       
                                                                                                                                 
class ListRightNowStatusV2(APIView):
    """
    list of status ordered by timestamp.
    """

    permission_classes = (IsAuthenticated,)
    
    def post(self, request, *args, **kwargs):
        
        location = request.data.get("location")
        
        countries = list(map(lambda x:x.lower(), location))
        
        lastrightnow_id = request.data
        if cache.get(lastrightnow_id):
            all_status = cache.get(lastrightnow_id)
            print("lastrightnow status from cache")
        else:
            all_status = Status.objects.filter(current_status='active', author__country__in = countries).order_by('-last_updated_at')
            cache.set(lastrightnow_id, all_status)
            print("lastrightnow status from DB")

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

                                                                                                                               
                                                                                                                                 
class GetTrendingStatusV2(APIView):
    """
    get trending status based on z-score for a country or globally.
    """        

    permission_classes = (IsAuthenticated, )
    pagination_class = LimitOffsetPagination
    
    def post(self, request, *args, **kwargs):
        location = request.data.get('location')
        
        countries = list(map(lambda x:x.lower(), location))
        
        gettrending_id = request.data
        if cache.get(gettrending_id):
            status = cache.get(gettrending_id)
            print("trending from cache")
        else:
            status = Status.objects.filter(author__country__in=countries,current_status="active")
            cache.set(gettrending_id, status)
            print("trending from DB")

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
                                                                                                                     
                
class GetBuzzingStatusV2(APIView):
    """
    API to get list of Buzzing groups.
    NOTE:API call from Node Server
    """

    permission_classes = (IsAuthenticated,)

    def post(self, request, *args, **kwargs):
        
        location = request.data.get('location')
        
        limit = request.data.get("limit")
        
        countries = list(map(lambda x:x.lower(), location))

        try:
            get_buzzing_group_request_url = CustomFileFormats.NODE_SERVER_DOMAIN + 'group/getBuzzingGroups/' 
            get_buzzing_group_node_response = requests.get(
                get_buzzing_group_request_url,
                headers={
                    'x-auth-server': CustomFileFormats.NODE_ADMIN_TOKEN,
                    'Content-Type':"application/json",
                },
                json={
                    'country': countries,
                    'limit': limit
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
        
           
                
class SearchStatusV2(APIView):
    """
    to search a phrase in a status or a keyword in status or fullname/username
    """

    permission_classes = (IsAuthenticated,)

    def post(self, request, *args, **kwargs):
        
        locations = request.data.get("location")
    
        searchString = request.data.get('search_phrase')
        
        searchstatus_id = request.data
        if cache.get(searchstatus_id):
            all_status = cache.get(searchstatus_id) 
            print("search status from cache")
        else:
        
            status1 = Status.objects.filter(Q(current_status='active')|Q(current_status='inactive'))

            all_status = []

            for location in locations:


                if location["country"] != "" and location["city"] != []:
                    cities = list(map(lambda x:x.lower(), location["city"]))
                    all_status.append(status1.filter(author__city__in = cities).order_by('-created_at'))

                elif location["country"] != "" and location["city"] == []:
                    all_status.append(status1.filter(author__country = location["country"].lower()).order_by('-created_at')) 

                elif (location["country"] == "" and location["city"] == []) or (location["country"] == "" and location["city"] != []):
                          response = {
                            'message':"country can't be empty",
                            'status':HTTP_400_BAD_REQUEST
                          }
                          return Response(response, status=HTTP_400_BAD_REQUEST)
            cache.set(searchstatus_id, all_status)
            print("search status from DB")
                    
                
        search_keywords = searchString.strip().split(" ")
        search_keywords=list(filter(None,search_keywords))
        for i in range(len(search_keywords)):
            if search_keywords[i]==" ": 
                del search_keywords[i]
            else :
                print(search_keywords[i],1)

        print(searchString,search_keywords)
        status_filtered_search = {}
        for key in search_keywords:
            filtered = []
            for status_queryset in all_status:
                filtered.extend(status_queryset.filter(content__icontains=key))
                
            print(filtered,key,"hello")
            for status in filtered:
                status_filtered_search[status] = status_filtered_search.get(status,0) + 1
        
        status_sorted_search = OrderedDict(sorted(status_filtered_search.items(),key=lambda kv:kv[1], reverse=True))
        status_search_list = list(status_sorted_search)

        if status_search_list:
            try:
                paginator = LimitOffsetPagination()
                paginated_list = paginator.paginate_queryset(status_search_list, request)
                data = SearchStatusSerializer(paginated_list, context={ 'request': request }, many=True).data

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
                data = SearchStatusSerializer(status_search_list, context={ 'request': request }, many=True).data
                response = {
                    'message':'success',
                    'body':data,
                    'status':HTTP_200_OK
                }
                return Response(response, status=HTTP_200_OK)

        response = {
            'message':'Success',
            'body':'No search result',
            'status':HTTP_200_OK
        }
        return Response(response, status=HTTP_200_OK)

    
class SearchUsersV2(APIView):
    """
    to search a phrase in a status or a keyword in status or fullname/username
    """

    permission_classes = (IsAuthenticated,)

    def post(self, request, *args, **kwargs):
        
        locations = request.data.get("location")
        
        searchString = request.data.get('search_phrase')
        
        user = self.request.user
        
        searchuser_id = request.data
        if cache.get(searchuser_id):
            users1 = cache.get(searchuser_id)
            print("search users from cache")
        else:

            users = Profile.objects.filter(Q(user__status='Activated')).prefetch_related("user").exclude(user=user)
            print(users)

            users1 = []

            for location in locations:


                if location["country"] != "" and location["city"] != []:
                    cities = list(map(lambda x:x.lower(), location["city"]))
                    users1.append(users.filter(city__in = cities))

                elif location["country"] != "" and location["city"] == []:
                    users1.append(users.filter(country = location["country"].lower())) 

                elif (location["country"] == "" and location["city"] == []) or (location["country"] == "" and location["city"] != []):
                          response = {
                            'message':"country can't be empty",
                            'status':HTTP_400_BAD_REQUEST
                          }
                          return Response(response, status=HTTP_400_BAD_REQUEST)
                        
            cache.set(searchuser_id, users1)
            print("search users from DB")
        
        print(users1)
        search_keywords = searchString.strip().split(" ")
        users_filtered_search = {}
        for key in search_keywords:
            
            filtered = []
            for users in users1:
                filtered.extend(users.filter(Q(full_name__icontains=key)|Q(user__username__icontains=key)|Q(country=key)|Q(city=key)))
        
            print(filtered,key)
            for us in filtered:
                users_filtered_search[us] = users_filtered_search.get(us,0) + 1
        
        users_sorted_search = OrderedDict(sorted(users_filtered_search.items(), key=lambda kv: kv[1], reverse=True))
        users_search_list = list(users_sorted_search)

        if users_search_list:
            try:
                paginator = LimitOffsetPagination()
                paginated_list = paginator.paginate_queryset(users_search_list, request)
                data = SearchUserSerializer(paginated_list, context={ 'request': request }, many=True).data

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
                data = SearchUserSerializer(users_search_list, context={ 'request': request }, many=True).data
                print(data)
                response = {
                    'message':'success',
                    'body':data,
                    'status':HTTP_200_OK
                }
                return Response(response, status=HTTP_200_OK)

        response = {
            'message':'Success',
            'body':'No search result',
            'status':HTTP_200_OK
        }
        return Response(response, status=HTTP_200_OK)

                
                
                
                
                
                
                
                
                
        