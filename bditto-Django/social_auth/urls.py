from django.urls import path

from .views import GoogleSocialAuthView, FacebookSocialAuthView, TwitterSocialAuthView, GoogleLoginPage, FacebookLoginPage

from .profile_social import CreateSocialProfile, RequestDeleteAccountLink, ValidateDeleteAccountLink, DeleteAccount

urlpatterns = [
    path('google/', GoogleSocialAuthView.as_view()),
    path('facebook/', FacebookSocialAuthView.as_view()),
    path('twitter/', TwitterSocialAuthView.as_view()),

    #login pages
    path('login/google/', GoogleLoginPage),
    path('login/facebook/', FacebookLoginPage),
    
    #create social profile
    path('create_social_profile/', CreateSocialProfile.as_view()),
    
    path("request-delete-account-link/", RequestDeleteAccountLink.as_view(), name="RequestDeleteAccountLink"),
    
    path('validate-delete-account-link/<slug:uidb64>/<slug:token>/', ValidateDeleteAccountLink.as_view(), name="ValidateAccountLink"),
    
    path("delete-account/", DeleteAccount.as_view(), name="DeleteAccount")
]
