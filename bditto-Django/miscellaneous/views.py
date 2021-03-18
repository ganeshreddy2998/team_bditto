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

from django_countries import countries
from .models import ReportIssue
from accounts.models import Profile
from status.models import Status
from .serializers import SearchStatusSerializer, SearchUserSerializer
from samePinch.permission import PartiallyBlockedPermission

from collections import OrderedDict

from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from django.views.decorators.vary import vary_on_cookie 


class GetCountries(APIView):
    """
    get list of countries.
    """
    
    def get(self, request, *args, **kwargs):
        

        response = {
            'message':'Success',
            'body':countries,
            'status':HTTP_200_OK
        }
        return Response(response, status=HTTP_200_OK)

class ReportAnyIssue(APIView):
    """
    report any issue related to the site.
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

        title = request.data.get('title').strip()
        description = request.data.get('description').strip()

        if title is None or description is None or len(title) == 0 or len(description) == 0:
            response = {
                'message':'Failed',
                'error':'both fields are mandatory',
                'status':HTTP_400_BAD_REQUEST
            }
            return Response(response, status=HTTP_400_BAD_REQUEST)

        ReportIssue.objects.create(user_associated=profile, title=title, description=description)
        response = {
            'message':'Success, reported successfully',
            'body':[],
            'status':HTTP_200_OK
        }
        return Response(response, status=HTTP_200_OK)

class SearchStatus(APIView):
    """
    to search a phrase in a status or a keyword in status or fullname/username
    """

    permission_classes = (IsAuthenticated,)

    def post(self, request, *args, **kwargs):
        searchString = request.data.get('search_phrase')
        country = request.data.get('country')
        city = request.data.get('city')

        status1 = Status.objects.filter(Q(current_status='active')|Q(current_status='inactive'))
        if country and country!='' and country!='global':
            status = status1.filter(author__country=country)
        if city and city!='' and city!='global':
            status1 = status1.filter(author__city=city)
        print(type(status1))
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
            filtered = status1.filter(content__icontains=key)
            print(filtered,key)
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

class SearchUsers(APIView):
    """
    to search a phrase in a status or a keyword in status or fullname/username
    """

    permission_classes = (IsAuthenticated,)

    def post(self, request, *args, **kwargs):
        searchString = request.data.get('search_phrase')
        country = request.data.get('country')
        city = request.data.get('city')
        user = self.request.user

        users = Profile.objects.filter(Q(user__status='Activated')|Q(user__status='Deactivated')).prefetch_related("user").exclude(user=user)
        if country and country!='' and country!='global':
            users = users.filter(country=country)
        if city and city!='' and city!='global':
            users = users.filter(city=city)
        
        search_keywords = searchString.strip().split(" ")
        users_filtered_search = {}
        for key in search_keywords:
            filtered = users.filter(Q(full_name__icontains=key)|Q(user__username__icontains=key)|Q(country=key)|Q(city=key))
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

        