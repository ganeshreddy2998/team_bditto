from django.urls import path,include

from .views import (
                CreateStatus, ChangeStatus ,CreateHashtags, 
                SetFavourite, GetMyFavourites, LikeStatus, 
                GetMyLikedStatus, ViewHistory, EditStatus,
                GetMyStatus, DeleteStatus,
                SearchHashtags, GetTopNHashtags,GetStatusByHashtags,
                ListRightNowStatus,GetTrendingStatus,GetBuzzingStatus,
                getSuggestions
            )

from .populate_data import (
                populate_status,
            )

from .updated_apis import getSuggestionsV2, GetStatusByHashtagsV2, ListRightNowStatusV2, GetTrendingStatusV2, GetBuzzingStatusV2, SearchStatusV2, SearchUsersV2

urlpatterns = [

    # Create new status API
    path('create-status/', CreateStatus.as_view(), name="CreateStatus"),

    # set status as active/inactive 
    path('change-status/', ChangeStatus.as_view(), name="ChangeStatus"),

    # Create/Fetch Hashtag
    path('create-update-count-hashtag/', CreateHashtags.as_view(), name='CreateHashtags'),

    # Set status as Favourite
    path('set-favourite/', SetFavourite.as_view(), name="SetFavourite"),

    # get list of all favourite status.
    path('get-my-favourites/', GetMyFavourites.as_view(), name="GetMyFavourites"),

    # like/unlike status
    path('like-status/', LikeStatus.as_view(), name="LikeStatus"),

    # get list of all liked status.
    path('get-my-liked-status/', GetMyLikedStatus.as_view(), name="GetMyLikedStatus"),

    # get list of all those status that user has ever joined.
    path('view-history/', ViewHistory.as_view(), name="ViewHistory"),

    # Edit status
    path('edit-status/', EditStatus.as_view(), name="EditStatus"),

    # get active/inactive/deleted/all status
    path('get-my-status/', GetMyStatus.as_view(), name="GetMyStatus"),

    # Delete your status
    path('delete-status/', DeleteStatus.as_view(), name='DeleteStatus'),

    # Get status by hashtags.
    path('get-status-by-hashtags/', GetStatusByHashtags.as_view(), name="GetStatusByHashtags"),

    # search hashtags
    path('search-hashtags/', SearchHashtags.as_view(), name="SearchHashtags"),

    # List right now status
    path('right-now-status/', ListRightNowStatus.as_view(), name="ListRightNowStatus"),

    # get list of top N hashtags
    path('get-topn-hashtags/', GetTopNHashtags.as_view(), name="GetTopNHashtags"),

    # get list of Trending status
    path('get-trending-status/', GetTrendingStatus.as_view(), name="GetTrendingStatus"),

    # Get buzzing status
    path('get-buzzing-status/', GetBuzzingStatus.as_view(), name="GetBuzzingGroups"),

    # get Suggestions list
    path('get-suggestions/', getSuggestions.as_view(), name="GetSuggestions"),

    # Upload dummy data
    path('upload-data/', populate_status, name="UploadDummyData"),
    
    #version2
    path('get-suggestions/v2/', getSuggestionsV2.as_view(), name="GetSuggestionsV2"),
    
    path('get-status-by-hashtags/v2/', GetStatusByHashtagsV2.as_view(), name="GetStatusByHashtagsV2"),
    
    path('right-now-status/v2/', ListRightNowStatusV2.as_view(), name="ListRightNowStatusV2"),
    
    path('get-trending-status/v2/', GetTrendingStatusV2.as_view(), name="GetTrendingStatusV2"),
    
    path('get-buzzing-status/v2/', GetBuzzingStatusV2.as_view(), name="GetBuzzingGroupsV2"),
    
    path('search-status/v2/', SearchStatusV2.as_view(), name="SearchStatusV2"),
    
    path('search-user/v2/', SearchUsersV2.as_view(), name="SearchUserV2"),

]