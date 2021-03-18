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
from django.shortcuts import get_object_or_404
from django.http import Http404
from django.db.models import Q

from samePinch import constants_formats as CustomFileFormats
from accounts.models import Profile
# from .models import Notifications
from .serializers import NotificationsSerializer
from notifications.models import Notification
from notifications.signals import notify

from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from django.views.decorators.vary import vary_on_cookie 


from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
import json

class getNotification(APIView):
    

    permission_classes = (IsAuthenticated, )
    pagination_classes=LimitOffsetPagination
    @method_decorator(cache_page(60))
    @method_decorator(vary_on_cookie)

    def get(self, request, *args, **kwargs):

        user=request.user
        objs=user.notifications.all().order_by("-timestamp")
        if objs.exists():
            try:
                paginator = LimitOffsetPagination()
                paginated_list = paginator.paginate_queryset(objs, request)
                data = NotificationsSerializer(paginated_list, context={ 'request': request }, many=True).data

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
                data = NotificationsSerializer(objs, context={ 'request': request }, many=True).data

                response = {
                    'message':'success',
                    'body':data,
                    'status':HTTP_200_OK
                }
                return Response(response, status=HTTP_200_OK)

        response = {
            'message':'No notifications found',
            'body':[],
            'status':HTTP_200_OK
        }
        return Response(response, status=HTTP_200_OK)


class NotificationSeen(APIView):
    """
    API to mark Notification as seen.
    NOTE: client will send a list of IDs
    """

    permission_classes = (IsAuthenticated,)

    def post(self, request, *args, **kwargs):
        notifIds = request.data.getlist('notifIds')
        user = self.request.user
        profile = user.userAssociated.all().first()
        
        for Id in notifIds:
            try:
                notifId = int(Id)
                notif = get_object_or_404(Notification, pk=notifId)

                if notif.recipient.pk != profile.user.pk:
                    response = {
                        'message':'Invalid Request',
                        'error':'Notification (' + str(notifId) + ') is not related to this user',
                        'status':HTTP_400_BAD_REQUEST
                    }
                    return Response(response, status=HTTP_400_BAD_REQUEST)

                notif.unread = False
                notif.save()
            except:
                response = {
                    'message':'Invalid Request !!',
                    'error':'Invalid notification Id '+Id,
                    'status':HTTP_400_BAD_REQUEST
                }
                return Response(response, status=HTTP_400_BAD_REQUEST)

        response = {
            'message':'Success, notifications marked as seen.',
            'body':[],
            'status':HTTP_200_OK
        }
        return Response(response, status=HTTP_200_OK)

class sendNotifications(APIView):
    """
    Used by node server to send notifications about message and starred message.
    """


    def post(self, request, *args, **kwargs):
        admin_token = request.data['admin_token']
        text = request.data.get('notification_text')
        receiverID = request.data.get('receiverID')
        notif_type = request.data.get('notification_type')

        try:
            userID = int(receiverID)
            user = get_object_or_404(Profile, pk=int(userID))
        except:
            response = {
                'message':"Invalid Request",
                'error':"Invalid receiverID",
                'status':HTTP_400_BAD_REQUEST
            }
            return Response(response, status=HTTP_400_BAD_REQUEST)
        
        if notif_type != 'message' and notif_type != 'liked_message':
            response = {
                'message':"Invalid Request",
                'error':"Invalid notification type",
                'status':HTTP_400_BAD_REQUEST
            }
            return Response(response, status=HTTP_400_BAD_REQUEST)

        try:
            metas = request.data.getlist('metas')
        except:
            metas = request.data.get('metas')
                
        if admin_token != CustomFileFormats.DJANGO_ADMIN_TOKEN:
            response = {
                'message':'Invalid Request!!',
                'error':'send correct admin token.',
                'status':HTTP_400_BAD_REQUEST
            } 
            return Response(response, status=HTTP_400_BAD_REQUEST)

        associated_ids = ''
        data={}
        print(metas)
        for mt in metas:
            #associated_ids += mt['key'].strip() + ':' + mt['value'].strip() +' '
            data[mt['key']]= mt['value']
            #     'messageID':id1,
            #     'conversationID': id2,
            #     'userID': id3,
            #     'username': id4
            # }
        data['userID']=receiverID
        data['username']=user.user.username
        notify.send(user.user,recipient=user.user,verb=notif_type, description=text,data=data)
        n=Notification.objects.filter(data={"data":data},recipient=user.user).order_by("-timestamp").first()
        d=NotificationsSerializer(n).data
        channel_layer = get_channel_layer()

        print(d,channel_layer.group_send)
        # Trigger message sent to group
        async_to_sync(channel_layer.group_send)(
            f"{user.user.id}", {
                            "type": "notifi",
                            "event": notif_type,
                            "data": str(d)})  
        response = {
            'message':'success',
            'body':[],
            'status':HTTP_200_OK
        }
        return Response(response, status=HTTP_200_OK)


class get_unread_notification_count(APIView):

    permission_classes = (IsAuthenticated, )
    @method_decorator(cache_page(60))
    @method_decorator(vary_on_cookie)
    def get(self, request, *args, **kwargs):
        user=request.user

        count=user.notifications.unread().count()
        return Response({"message":count}, status=HTTP_200_OK)

