from django.urls import path,include

from .notify_views import (getNotification, NotificationSeen, sendNotifications,get_unread_notification_count
            )

urlpatterns = [
     # get list of all notifications
    path('get-notifications/', getNotification.as_view(), name="GetNotifications"),

    # mark notifications as seen
    path('notification-seen/', NotificationSeen.as_view(), name="NotificationSeen"),

    # send notifications API for Node server
    path('send-notification/', sendNotifications.as_view(), name="SendNotifications"),

    path('get-unread-notification-count/', get_unread_notification_count.as_view(), name="get_unread_notification_count"),


]