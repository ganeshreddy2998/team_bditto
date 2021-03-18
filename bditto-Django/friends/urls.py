from django.urls import path,include

from .views import (
                SendFriendRequest, ActionFriendRequest, UnFriendUser,
                ToggleBlock, ReportUser, GetBlockedUsers, ViewUserStatus,
                FriendRequestsView, JoinLeaveGroup, GetGroupInfo,
                NodeGetGroupInfo, CheckFriendShip
            )

urlpatterns = [
    # Send Friend Request API
    path('send-request/', SendFriendRequest.as_view(), name="SendFriendRequest"),

    # Delete, Reject or Accept Friend Request
    path('action-request/', ActionFriendRequest.as_view(), name="ActionFriendRequest"),

    # UnFriend a Friend
    path('unfriend/', UnFriendUser.as_view(), name="UnFriend"),

    # Block or Unblock a user
    path('toggle-block/', ToggleBlock.as_view(), name="ToggleBlock"),

    # Report a user
    path('report-user/', ReportUser.as_view(), name="ReportUser"),

    # Get blocked users list
    path('get-blocked-users/', GetBlockedUsers.as_view(), name="GetBlockedUsers"),

    # Get all active and inactive status of a particular user
    path('get-user-status/', ViewUserStatus.as_view(), name="GetUserStatus"),

    # Get all pending requests
    path('get-pending-requests/', FriendRequestsView.as_view(), name="GetPendingRequests"),

    # Leave or Join group
    path('join-leave-group/', JoinLeaveGroup.as_view(), name="JoinLeaveGroup"),

    # get group info
    path('get-group-info/', GetGroupInfo.as_view(), name="GetGroupInfo"),

    # get group info for node server
    path('node-get-group-info/', NodeGetGroupInfo.as_view(), name="NodeGetGroupInfo"),

    # check friendship status API for Node server
    path('check-friendship/', CheckFriendShip.as_view(), name="CheckFriendShip"),

]