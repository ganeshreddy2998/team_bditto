import random
import string

import requests
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import (authenticate, login, logout,
                                 update_session_auth_hash)
from django.contrib.auth.hashers import check_password
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.contrib.sites.shortcuts import get_current_site
from django.core.mail import EmailMessage, send_mail
from django.http import Http404
from django.template.loader import render_to_string
from django.utils.encoding import force_bytes, force_text
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from friends.models import FriendRequest
from requests.exceptions import HTTPError
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.decorators import api_view
from rest_framework.generics import (CreateAPIView, DestroyAPIView,
                                     ListAPIView, RetrieveAPIView,
                                     UpdateAPIView)
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.status import (HTTP_200_OK, HTTP_400_BAD_REQUEST,
                                   HTTP_401_UNAUTHORIZED)
from rest_framework.views import APIView
from samePinch import constants_formats as CustomConstants
from samePinch.permission import PartiallyBlockedPermission
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
from status.models import Status

from .models import Profile, User
from .serializers import (ForgotPasswordEmailSerializer, ProfileSerializer,
                          RegistrationSerializer, SetNewPasswordSerializer)
from .tokens import account_activation_token

from django.shortcuts import render

@api_view(['POST',])
def register_user(request):
    if request.method == 'POST':
        email = request.data.get('email').lower()
        username = request.data.get('username')
        if username == email:
            response = {
                'message':'SignUp failed !!',
                'error':"Username"+str("can't")+" be the same as email",
                'status':HTTP_400_BAD_REQUEST
            }

        check_user = User.objects.filter(email=email).first()
        check_username = User.objects.filter(username__iexact=username).first()

        if check_user and not check_user.is_active:
            check_user.delete()
            check_username = ''
            
        filtered_user_by_email = User.objects.filter(email=email)
        if filtered_user_by_email.exists() and filtered_user_by_email[0].auth_provider != 'email':
            response = {
                "message": "Login failed",
                "error": 'Please continue your login using ' + filtered_user_by_email[0].auth_provider,
                'status':HTTP_401_UNAUTHORIZED
            }
            return Response(response, status=HTTP_401_UNAUTHORIZED)

        if check_username:
            response = {
                'message':'SignUp failed !!',
                'error':'Username is already taken',
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
        print(request.data)
        serializer = RegistrationSerializer(data = request.data)
        if serializer.is_valid():
            account = serializer.save()
            
            full_name = request.data.get('full_name')
            country = request.data.get('country').lower()
            city = request.data.get('city').lower()
            gender = request.data.get('gender')

            Profile.objects.create(
                            user=account, country=country, 
                            city=city, full_name=full_name, 
                            gender=gender
                        )

            current_site = CustomConstants.EMAIL_DOMAIN +"/account-activation"
            mail_subject = '[noreply] Activate your Account'
            msg = 'Thanks for Signing up with Bditto.'

            message = render_to_string('acc_email_active.html', {
                'user': account,
                'domain': current_site,
                'msg':msg,
                'uid':urlsafe_base64_encode(force_bytes(account.pk)),
                'token':account_activation_token.make_token(account),
            })

            to_email = [account.email]
            from_email = settings.SENDER_EMAIL

            email = Mail(
                from_email=from_email,
                to_emails=to_email,
                subject=mail_subject,
                html_content=message,
            )
            try:
                sg = SendGridAPIClient(settings.SENDGRID_API_KEY)
                response = sg.send(email)
            except Exception as e:
                response = {
                    'message':'User Registration failed',
                    'error':"Mail not sent",
                    'status':HTTP_400_BAD_REQUEST
                }
                return Response(response, status=HTTP_400_BAD_REQUEST)

            response = {
                'message':'User registered successfully, Please verify your accoumt using the link sent via email',
                'body':[],
                'status':HTTP_200_OK
            }
            return Response(response, status=HTTP_200_OK)

        else:
            response = {
                'message':'User Registration failed',
                'error':serializer.errors,
                'status':HTTP_401_UNAUTHORIZED
            }
        return Response(response, status=HTTP_401_UNAUTHORIZED)

@api_view(['GET',])
def activate(request, uidb64, token):
    try:
        uid = force_text(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
        email = user.email

    except(TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None
        email=None

    if user is not None and account_activation_token.check_token(user, token):
        user.is_active = True
        user.save()
        profile = user.userAssociated.all().first()

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

            node_response.raise_for_status()

            response = {
                    'message':'Account Activation done',
                    'body':'account activated',
                    'status':HTTP_200_OK
            }
            return Response(response, status=HTTP_200_OK)
            
        except Exception as e:
            response = {
                'message':'Account Activation failed',
                'error':str(e),
                'status': HTTP_401_UNAUTHORIZED
            }
            return Response(response, status=HTTP_401_UNAUTHORIZED)

    else:
        if user and not user.is_active:
            User.objects.filter(email=email).delete()
        response = {
                'message':'Account activation failed',
                'error':'Token expired',
                'status':HTTP_401_UNAUTHORIZED
            }
        return Response(response, status=HTTP_401_UNAUTHORIZED)

@api_view(['POST',])
def login_user(request):
    if request.method == 'POST':
        email = password = ''
        email = request.data.get('email').lower()
        password = request.data.get('password')
        user = authenticate(email=email, password=password)
        obj = User.objects.filter(email=email).first()

        if obj is None:
            message = "You do not have an account please signup to continue."
            response = {
                'message':message,
                'error':'error',
                'status':HTTP_401_UNAUTHORIZED
            }
            return Response(response, status=HTTP_401_UNAUTHORIZED)

        elif user is None:
            message = "Invalid Password !!"
            response = {
                'message':message,
                'error':'error',
                'status':HTTP_401_UNAUTHORIZED
            }
            return Response(response, status=HTTP_401_UNAUTHORIZED)

        elif user.status == 'Blocked' or user.status == 'Deleted':
            message = "Your Account is {}".format(user.status)
            response = {
                'message':message,
                'error':'error',
                'status':HTTP_401_UNAUTHORIZED
            }
            return Response(response, status=HTTP_401_UNAUTHORIZED)

        elif user.is_active:
            
            filtered_user_by_email = User.objects.filter(email=email)
            user = authenticate(email=email, password=password)

            if filtered_user_by_email.exists() and filtered_user_by_email[0].auth_provider != 'email':
                response = {
                    "message": "Login failed",
                    "error": 'Please continue your login using ' + filtered_user_by_email[0].auth_provider,
                    'status':HTTP_401_UNAUTHORIZED
                }
                return Response(response, status=HTTP_401_UNAUTHORIZED)
            
            try:
                token = Token.objects.get(user=user).key
                if token is None:
                    raise Http404
            except:
                response = {
                    'message':'Login Failed !!',
                    'error':'Invalid Token',
                    'status':HTTP_401_UNAUTHORIZED
                }
                return Response(response, status=HTTP_401_UNAUTHORIZED)

            profile = user.userAssociated.all().first()
            data = ProfileSerializer(profile).data
            data['token'] = token

            try:
                current_site = CustomConstants.EMAIL_DOMAIN
            
                request_url = CustomConstants.NODE_SERVER_DOMAIN + 'user/score/' 
                node_response = requests.get(
                    request_url,
                    headers={
                        'x-auth-server': CustomConstants.NODE_ADMIN_TOKEN,
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
                    'message':'Login successfull.',
                    'body':data,
                    'status':HTTP_200_OK
                }
                return Response(response, status=HTTP_200_OK)
                
            except Exception as e:
                response = {
                    'message':'Account Activation failed',
                    'error':str(e),
                    'status': HTTP_400_BAD_REQUEST
                }
                return Response(response, status=HTTP_400_BAD_REQUEST)

        else:
            message = "Your account is not yet activated, please click on the activation link sent on your email or Signup again."
            response = {
                'message':message,
                'error':'error',
                'status':HTTP_400_BAD_REQUEST
            }
            return Response(response, status=HTTP_400_BAD_REQUEST)

class PasswordResetEmail(APIView):
    serializer_class = ForgotPasswordEmailSerializer

    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        
        email = request.data.get('email')
        user = User.objects.filter(email=email).first()
        if user:
            print(user.status)
            if user.status == 'Blocked' or user.status == 'Deleted':
                message = "Your Account is {}".format(user.status)
                response = {
                    'message':message,
                    'error':'Request not allowed.',
                    'status':HTTP_400_BAD_REQUEST
                }
                return Response(response, status=HTTP_400_BAD_REQUEST)

            uidb64 = urlsafe_base64_encode(force_bytes(user.pk))
            token = PasswordResetTokenGenerator().make_token(user)

            current_site = CustomConstants.EMAIL_DOMAIN + "/forget-password-reset"
            mail_subject = '[noreply] Reset your Password'
            msg = 'You will be redirected to the password reset page.'

            message = render_to_string('password_reset_link.html', {
                'user': user,
                'domain': current_site,
                'msg':msg,
                'uid':uidb64,
                'token':token,
            })

            to_email = [user.email]
            from_email = settings.SENDER_EMAIL

            email = Mail(
                from_email=from_email,
                to_emails=to_email,
                subject=mail_subject,
                html_content=message,
            )
            try:
                sg = SendGridAPIClient(settings.SENDGRID_API_KEY)
                response = sg.send(email)
            except Exception as e:
                response = {
                    'message':'User Registration failed',
                    'error':e,
                    'status':HTTP_400_BAD_REQUEST
                }
                return Response(response, status=HTTP_400_BAD_REQUEST)

            response = {
                "message":"Password reset link sent on your mail.",
                "status":HTTP_200_OK
            }
            return Response(response, status=HTTP_200_OK)

        else:
            response = {
                "message":"Enter Correct email",
                "status":HTTP_400_BAD_REQUEST
            }
        
        return Response(response, status=HTTP_400_BAD_REQUEST)

class PasswordTokenCheck(APIView):
    def get(self, request, uidb64, token):
        try:
            uid = force_text(urlsafe_base64_decode(uidb64))
            user = User.objects.get(pk=uid)
            email = user.email

        except(TypeError, ValueError, OverflowError, User.DoesNotExist):
            user = None
            email=None

        if user is not None:
            if PasswordResetTokenGenerator().check_token(user, token):
                response = {
                    'message':'Credentials Verified',
                    'success':True,
                    'token':token,
                    'uidb64':uidb64,
                    'status':HTTP_200_OK
                }
                return Response(response, status=HTTP_200_OK)

            return Response({
                'error':'Token expired',
                'status':HTTP_400_BAD_REQUEST
            }, status=HTTP_400_BAD_REQUEST)

        else:      
            response = {
                    'message':'Password Reset Failed !!',
                    'error':'error',
                    'status':HTTP_400_BAD_REQUEST
                }
            return Response(response, status=HTTP_400_BAD_REQUEST)

class SetNewPassword(APIView):
    serializer_class = SetNewPasswordSerializer

    def patch(self, request):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)

        return Response({
            'success':True,
            'message':'Password reset Successful.',
            'status':HTTP_200_OK
        }, status=HTTP_200_OK)

class ChangePassword(APIView):
    permission_classes=(IsAuthenticated,)

    def post(self, request, *args, **kwargs):
        
        old_password = request.data.get('old_password')
        new_password = request.data.get('new_password')
        confirm_password = request.data.get('confirm_password')
        
        user = self.request.user
        
        if user.auth_provider != "email":
            response = {
                "message": "Change password failed",
                "error": "Social user can't change their password",
                "status": HTTP_400_BAD_REQUEST
            }
            return Response(response, status=HTTP_400_BAD_REQUEST)
        
        if user.status == 'Blocked' or user.status == 'Deleted':
            message = "Your Account is {}".format(user.status)
            response = {
                'message':message,
                'error':'error',
                'status':HTTP_400_BAD_REQUEST
            }
            return Response(response, status=HTTP_400_BAD_REQUEST)
        
        if not user.check_password(old_password):
            response = {
                    'message':'Password Reset Failed !!',
                    'error':'Old Passowrd is wrong, Please enter correct password.',
                    'status':HTTP_400_BAD_REQUEST
            }
            return Response(response, status=HTTP_400_BAD_REQUEST)

        if new_password != confirm_password:
            response = {
                    'message':'Password Reset Failed !!',
                    'error':'new password and confirm password are different',
                    'status':HTTP_400_BAD_REQUEST
            }
            return Response(response, status=HTTP_400_BAD_REQUEST)

        if new_password == old_password:
            response = {
                    'message':'Password Reset Failed !!',
                    'error':'new password and old password are same, please enter a different password.',
                    'status':HTTP_400_BAD_REQUEST
            }
            return Response(response, status=HTTP_400_BAD_REQUEST)

        if len(new_password) < 8:
            response = {
                    'message':'Password Reset Failed !!',
                    'error':'Password too short, password length must me between 8 to 16 characters.',
                    'status':HTTP_400_BAD_REQUEST
            }
            return Response(response, status=HTTP_400_BAD_REQUEST)

        user.set_password(new_password)
        user.save()

        response = {
            'message':'Password changed Successfully',
            'body':[],
            'status':HTTP_200_OK
        }
        return Response(response, status=HTTP_200_OK)

class ValidateToken(APIView):
    permission_classes=(IsAuthenticated,)

    def post(self, request, *args, **kwargs):
        try:
            request_type = request.data.get('request_type')
            admin_token = request.data.get('admin_token')
            
            if admin_token != CustomConstants.DJANGO_ADMIN_TOKEN:
                response = {
                    'message':'Invalid Request!!',
                    'error':'send correct admin token.',
                    'status':HTTP_400_BAD_REQUEST
                } 
                return Response(response, status=HTTP_400_BAD_REQUEST)

            if request_type != 'Write' and request_type !='Read':
                response = {
                    'message':'Invalid Request Type!!',
                    'error':'only Read and Write requests are allowed.',
                    'status':HTTP_400_BAD_REQUEST
                } 
                return Response(response, status=HTTP_400_BAD_REQUEST)

            user = self.request.user
            if user.status == 'Blocked':
                response = {
                    'message':'User is blocked',
                    'error':'User is blocked',
                    'status':HTTP_400_BAD_REQUEST
                } 
                return Response(response, status=HTTP_400_BAD_REQUEST)

            if (request_type == 'Write' and user.status == 'Activated') or (request_type == 'Read' and user.status != 'Blocked' and user.status != 'Deleted'):
                profile = user.userAssociated.all().first()
                data = ProfileSerializer(profile).data
                response = {
                    'message':'User is authorized',
                    'body':data,
                    'status':HTTP_200_OK
                }
                return Response(response, status=HTTP_200_OK)
            
            response = {
                'message':'User is unauthorized',
                'error':'User is partially blocked',
                'status':HTTP_400_BAD_REQUEST
            } 
            return Response(response, status=HTTP_400_BAD_REQUEST)

        except:
            response = {
                'message':'Invalid Request!!',
                'error':'Invalid Request!!',
                'status':HTTP_400_BAD_REQUEST
            } 
            return Response(response, status=HTTP_400_BAD_REQUEST)

class DeleteAccount(APIView):
    permission_classes = (IsAuthenticated, PartiallyBlockedPermission)

    def post(self, request, *args, **kwargs):
        current_password = request.data.get('current_password')
        confirm_password = request.data.get('confirm_password')
        
        user = self.request.user
        profile = user.userAssociated.all().first()
        
        if not user.check_password(current_password):
            response = {
                'message':'Account deletion failed !!',
                'error':'Passowrd is wrong, Please enter correct password.',
                'status':HTTP_400_BAD_REQUEST
            }
            return Response(response, status=HTTP_400_BAD_REQUEST)

        if current_password != confirm_password:
            response = {
                    'message':'Account deletion failed !!!@',
                    'error':"Passowrds didn't match, Please enter correct password.",
                    'status':HTTP_400_BAD_REQUEST
            }
            return Response(response, status=HTTP_400_BAD_REQUEST)

        deleted_suffix = ''.join(random.choices(string.ascii_uppercase + string.digits, k = 4))    
        deleted_suffix = deleted_suffix.join(random.choices(string.ascii_lowercase, k=2))
        deleted_suffix += str(user.pk)

        # all_status = Status.objects.filter(author=profile)

        # if all_status:
        #     all_status.update(current_status='inactive')

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

        response = {
            'message':'Account Deleted Successfully.',
            'body':[],
            'status':HTTP_200_OK
        }
        return Response(response, status=HTTP_200_OK)