from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.status import (HTTP_200_OK, HTTP_400_BAD_REQUEST,
                                   HTTP_401_UNAUTHORIZED)
from rest_framework.views import APIView
from rest_framework import status

from accounts.models import Profile, User

from django.core.exceptions import ValidationError
from django.conf import settings

from accounts.serializers import ProfileSerializer

from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.contrib.sites.shortcuts import get_current_site
from django.core.mail import EmailMessage, send_mail
from django.http import Http404
from django.template.loader import render_to_string
from django.utils.encoding import force_bytes, force_text
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode

from samePinch import constants_formats as CustomConstants
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

from .profile_serializers import DeleteSocialAccountSerializer

class CreateSocialProfile(APIView):
    permission_classes=(IsAuthenticated,)

    def post(self, request, *args, **kwargs):
        
        user = request.user
        profile = user.userAssociated.all().first()
        
        try:
        
            if user.auth_provider == "email":
                raise ValidationError("You must be the social user to use this API")


            full_name = request.data.get('full_name')
            country = request.data.get('country').lower()
            city = request.data.get('city').lower()
            gender = request.data.get('gender')
            
            if (full_name=="" or country=="") or ("full_name" not in request.data or "country" not in request.data):
                raise ValidationError("full name and country are mandatory")
                
            profile=Profile.objects.filter(id=profile.id)
            profile_user = profile.first()
            
            profile.update(
                full_name=full_name,
                country=country,
                city=city,
                gender=gender
            )


        except Exception as e:
            response = {
                    "message": "Profile creation failed",
                    "error": str(e),
                    "status": HTTP_400_BAD_REQUEST
                }
            return Response(response, status=HTTP_400_BAD_REQUEST)
        
        profile=Profile.objects.filter(id=profile_user.id).first()
        
        data = ProfileSerializer(profile).data
        
        response = {
            "message": "Profile created for social user successfully",
            "body": data,
            "status": HTTP_200_OK
        }
        return Response(response, status=HTTP_200_OK)
        
        
class RequestDeleteAccountLink(APIView):
    permission_classes = (IsAuthenticated,)
    
    def post(self, request, *args, **kwargs):
        
        user = self.request.user
            
        
        if user.status in ["Blocked", "Deactivated"]:
            response = {
                "message": "Account Deletion Failed!!",
                "error": "User's account must be active for deletion",
                "status": HTTP_401_UNAUTHORIZED
            }
            return Response(response, status=HTTP_401_UNAUTHORIZED)
        
        if user.status == "Deleted":
            response = {
                "message": "Account Deletion Failed!!",
                "error": "Your social account is already deleted",
                "status": HTTP_400_BAD_REQUEST
            }
            return Response(response, status=HTTP_400_BAD_REQUEST)
        
        uidb64 = urlsafe_base64_encode(force_bytes(user.pk))
        token = PasswordResetTokenGenerator().make_token(user)

        current_site = CustomConstants.EMAIL_DOMAIN + "/delete-your-account"
        mail_subject = '[noreply] Delete your account'
        msg = 'You will be redirected to the delete account page.'

        message = render_to_string('delete_account_page.html', {
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
                'message':'Delete account failed',
                'error':str(e),
                'status':HTTP_400_BAD_REQUEST
            }
            return Response(response, status=HTTP_400_BAD_REQUEST)

        response = {
            "message":"Delete account link sent on your mail.",
            "status":HTTP_200_OK
        }
        return Response(response, status=HTTP_200_OK)

    
class ValidateDeleteAccountLink(APIView):
    def get(self, request, uidb64, token):
        try:
            uid = force_text(urlsafe_base64_decode(uidb64))
            user = User.objects.get(pk=uid)
            email = user.email

        except(TypeError, ValueError, OverflowError, User.DoesNotExist):
            user = None
            email=None
            
        if user.status == "Deleted":
            response = {
                "message": "Account Deletion Failed!!",
                "error": "Your social account is already deleted",
                "status": HTTP_400_BAD_REQUEST
            }
            return Response(response, status=HTTP_400_BAD_REQUEST)

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
                    'message':'Delete Account Failed !!',
                    'error':'error',
                    'status':HTTP_400_BAD_REQUEST
                }
            return Response(response, status=HTTP_400_BAD_REQUEST)
        
class DeleteAccount(APIView):
    
    permission_classes = (IsAuthenticated,)
    serializer_class = DeleteSocialAccountSerializer
    
    def delete(self, request, *args, **kwargs):
        
        user = self.request.user
        profile = user.userAssociated.all().first()
        
        if user.status == "Deleted":
            response = {
                "message":"Account Deletion Failed!!",
                "error": "Your account is already deleted",
                "status": HTTP_400_BAD_REQUEST
            }
            return Response(response, status=HTTP_400_BAD_REQUEST)
        
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)

        return Response({
            'success':True,
            'message':'Account Deletion Successful.',
            'status':HTTP_200_OK
        }, status=HTTP_200_OK)
        
        
        
    