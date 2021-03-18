
from django.contrib.auth import authenticate
from accounts.models import User
import os
import random
from rest_framework.exceptions import AuthenticationFailed
from decouple import config

from rest_framework.authtoken.models import Token
from django.http import Http404

from rest_framework.status import (HTTP_200_OK, HTTP_400_BAD_REQUEST,
                                   HTTP_401_UNAUTHORIZED)

from accounts.serializers import ProfileSerializer

from samePinch import constants_formats as CustomConstants

import requests

def generate_username(name):

    username = "".join(name.split(' ')).lower()
    if not User.objects.filter(username=username).exists():
        return username
    else:
        random_username = username + str(random.randint(0, 1000))
        return generate_username(random_username)


def register_social_user(provider, user_id, email, name):
    filtered_user_by_email = User.objects.filter(email=email)

    if filtered_user_by_email.exists():

        if provider == filtered_user_by_email[0].auth_provider:

            registered_user = authenticate(
                email=email, password=config('SOCIAL_SECRET'))
            
            try:
                token = Token.objects.get(user=registered_user).key
                print(token)
                if token is None:
                    raise Http404
            except:
                return {
                    'message':'Login Failed !!',
                    'error':'Invalid Token',
                    'status':HTTP_401_UNAUTHORIZED
                }
            
            profile = registered_user.userAssociated.all().first()
            data = ProfileSerializer(profile).data
            
            data["token"] = token
            
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
            
                return data
            except Exception as e:
                raise AuthenticationFailed(str(e))

        else:
            raise AuthenticationFailed(
                detail='Please continue your login using ' + filtered_user_by_email[0].auth_provider)

    else:
        user = {
            'username': generate_username(name), 'email': email,
            'password': config('SOCIAL_SECRET')}
        
        user = User.objects.create_user(**user)
        user.is_verified = True
        user.auth_provider = provider
        user.save()
        print(user)
        
        try:
            token = Token.objects.get(user=user).key
            if token is None:
                raise Http404
        except:
            return {
                'message':'Login Failed !!',
                'error':'Invalid Token',
                'status':HTTP_401_UNAUTHORIZED
            }
        
        new_user = authenticate(
            email=email, password=config('SOCIAL_SECRET'))
        return {
            'email': new_user.email,
            'username': new_user.username,
            "token": token
        }
