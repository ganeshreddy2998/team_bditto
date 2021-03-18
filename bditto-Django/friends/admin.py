from django.contrib import admin

from .models import FriendRequest, BlockedUsers, ReportUsers, Groups

    
# FriendRequest model admin Configuration
@admin.register(FriendRequest)
class FriendRequestAdmin(admin.ModelAdmin):
    list_display = ('sender', 'receiver', 'request_status', 'sent_at')
    list_filter = ('request_status',)

# BlockedUsers model admin Configuration
@admin.register(BlockedUsers)
class BlockedUsersAdmin(admin.ModelAdmin):
    list_display = ('blocked_by', 'user_blocked', 'blocked_on',)

# ReportUsers model admin Configuration
@admin.register(ReportUsers)
class ReportUsersAdmin(admin.ModelAdmin):
    list_display = ('reported_by', 'user_reported', 'status', 'reported_on',)
    list_filter = ('status',)
    
# Groups model admin Configuration
@admin.register(Groups)
class GroupsAdmin(admin.ModelAdmin):
    list_display = ('status_id', 'created_on',)
    
