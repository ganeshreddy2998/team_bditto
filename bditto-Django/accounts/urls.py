from django.urls import path,include

from .views import (
                register_user, activate, PasswordResetEmail, login_user,
                PasswordTokenCheck, SetNewPassword, ChangePassword,
                ValidateToken, DeleteAccount
            )

from .profile_views import (
                MyProfileView, EditProfile, UserProfileView, GetFriendList,
                SearchFriend, ToggleOnline
            )

#from .social_views import (
#                FacebookLogin, GoogleLogin,TwitterLogin
#            )

urlpatterns = [
    # Authentication APIs
    path('signup/', register_user, name="registerNewUser"),
    path('login/', login_user, name="LoginView"),
    path('activate/<slug:uidb64>/<slug:token>/', activate, name='ActivateUser'),
    path('request-password-reset/', PasswordResetEmail.as_view(), name="SendPasswordResetEmail"),
    path('password-reset/<slug:uidb64>/<slug:token>/', PasswordTokenCheck.as_view(), name="PasswordResetConfirm"),
    path('password-reset-complete/',SetNewPassword.as_view(), name="PasswordResetComplete"),
    path('change-password/', ChangePassword.as_view(), name="ChangePassword"),

    # Validation APIs
    path('validate-token/', ValidateToken.as_view(), name="ValidateToken"),

    # Social login
#    path('social/facebook/', FacebookLogin.as_view(), name='socialaccount_signup_facebook'),
#    path('social/google/', GoogleLogin.as_view(), name='socialaccount_signup_google'),
#    path('social/twitter/', TwitterLogin.as_view(), name='socialaccount_signup_twitter'),
#    path('social/rest-auth/login/', FacebookLogin.as_view(), name='authorize'),

    # Profile APIs
    path('get-my-profile/',MyProfileView.as_view(), name="GetMyProfile"),
    path('edit-profile/', EditProfile.as_view(), name="EditProfile"),
    path('get-user-profile/', UserProfileView.as_view(), name="GetUserProfile"),

    # Delete Account
    path('delete-account/', DeleteAccount.as_view(), name="DeleteAccount"),

    # Friends list API
    path('get-friends-list/', GetFriendList.as_view(), name="GetFriendsList"),

    # Search friend
    path('search-friend/', SearchFriend.as_view(), name="SearchFriend"),

    # Toggle online/offline status of user
    path('toggle-online/', ToggleOnline.as_view(), name="ToggleOnline"),
    

]