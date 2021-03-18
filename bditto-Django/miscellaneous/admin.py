from django.contrib import admin
from .models import ReportIssue

# ReportIssue model admin Configuration
@admin.register(ReportIssue)
class ReportIssueAdmin(admin.ModelAdmin):
    list_display = ('user_associated', 'title', 'status', 'reported_on',)
    list_filter = ('status',)
