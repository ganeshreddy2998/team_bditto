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
from django.core.exceptions import ValidationError

from accounts.models import User
from rest_framework.authtoken.models import Token

import random
import string

from friends.models import FriendRequest
from samePinch import constants_formats as CustomConstants

class DeleteSocialAccountSerializer(serializers.Serializer):
    
    token = serializers.CharField(min_length=1, write_only=True)
    uidb64 = serializers.CharField(min_length=1, write_only=True)
    
    class Meta:
        fields = ['token', 'uidb64']

    def validate(self, attrs):
        try:
            
            token = attrs.get('token')
            uidb64 = attrs.get('uidb64')
            uid = force_text(urlsafe_base64_decode(uidb64))
            user = User.objects.get(pk=uid)
            
            profile = user.userAssociated.all().first()

            if not PasswordResetTokenGenerator().check_token(user, token):
                raise AuthenticationFailed('Reset link is valid', 401)
                
            deleted_suffix = ''.join(random.choices(string.ascii_uppercase + string.digits, k = 4))    
            deleted_suffix = deleted_suffix.join(random.choices(string.ascii_lowercase, k=2))
            deleted_suffix += str(user.pk)


            sent_requests = FriendRequest.objects.filter(sender=profile)
            received_requests = FriendRequest.objects.filter(receiver=profile)

            friends_id = []

            for req in sent_requests:
                friends_id.append(req.pk)
            for req in received_requests:
                friends_id.append(req.pk)

            try:
                request_url = CustomConstants.NODE_SERVER_DOMAIN + 'user/friendship' 
                node_response = requests.post(
                    request_url,
                    headers={
                        'x-auth-server': CustomConstants.NODE_ADMIN_TOKEN,
                        'Content-Type':"application/json",
                    },
                    json={
                        'user': profile.pk,
                        'friends': friends_id
                    }
                )

                node_response.raise_for_status()

            except Exception as e:
                response = {
                    'message':'Account deletion failed !!',
                    'error':str(e),
                    'status':HTTP_400_BAD_REQUEST
                }
                return Response(response, status=HTTP_400_BAD_REQUEST)

            sent_requests.delete()
            received_requests.delete()

            user.username = 'deleted<{}>'.format(deleted_suffix)
            user.status = 'Deleted'
            user.save()
            user.refresh_from_db()

            try:
                current_site = CustomConstants.EMAIL_DOMAIN
                if profile.avatar:
                    profile_url = profile.avatar.url
                else:
                    profile_url = ''

                request_url = CustomConstants.NODE_SERVER_DOMAIN + 'user/' 
                node_response = requests.post(
                    request_url,
                    headers={
                        'x-auth-server': CustomConstants.NODE_ADMIN_TOKEN,
                        'Content-Type':"application/json",
                    },
                    json={
                        'userID': profile.pk,
                        'fullname': profile.full_name,
                        'username': user.username,
                        'profileURL': profile_url
                    }
                )

            except Exception as e:
                response = {
                    'message':'User deletion failed on Node server.',
                    'error':str(e),
                    'status': HTTP_400_BAD_REQUEST
                }
                return Response(response, status=HTTP_400_BAD_REQUEST)

            token = Token.objects.get(user=user).delete()

            return super().validate(attrs)
        except Exception as e:
            raise ValidationError(str(e))