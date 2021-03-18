from django.urls import path
from django.contrib.auth.views import LogoutView

from .views import (
                    admin_home_page, active_users_view, deactive_users_view,
                    blocked_users_view, deleted_users_view, reported_users_view,
                    active_status_view, inactive_status_view, deleted_status_view,
                    pending_issues_view, discarded_issues_view, resolved_issues_view,
                    user_detail_page, change_user_status, issues_detail_view,
                    change_issue_status, report_user_page, change_user_report_status,
                    status_detail_page, change_status_status, admin_login ,status_graph,user_graph,status_created_graph
                )

urlpatterns = [
    path('login/', admin_login, name="AdminLogin"),
    path('logout/', LogoutView.as_view(template_name='logout.html/'),name='logoutpage', kwargs={'next_page':'AdminLogin'}),

    path('', admin_home_page, name="AdminHomePage"),
    path('active/users/', active_users_view, name="ActiveUsers"),
    path('deactive/users/', deactive_users_view, name="DeactiveUsers"),
    path('deleted/users/', deleted_users_view, name="DeletedUsers"),
    path('blocked/users/', blocked_users_view, name="BlockedUsers"),
    path('reported/users/', reported_users_view, name="ReportedUsers"),

    path('active/status/', active_status_view, name="ActiveStatus"),
    path('inactive/status/', inactive_status_view, name="InactiveUsers"),
    path('deleted/status/', deleted_status_view, name="DeletedStatus"),

    path('pending/issues/', pending_issues_view, name="PendingIssues"),
    path('resolved/issues/', resolved_issues_view, name="ResolvedIssues"),
    path('discarded/issues/', discarded_issues_view, name="DiscardedIssues"),

    path('user/profile/<str:slug>/', user_detail_page, name="UserDetailPage"),
    path('change-user-status/', change_user_status, name="ChangeUserStatus"),

    path('issues/<str:slug>/', issues_detail_view, name="IssuesDetailView"),
    path('change-issue-status/', change_issue_status, name="ChangeIssueStatus"),

    path('report/user/<str:slug>/', report_user_page, name="ReportUserPage"),
    path('change-report-user-status/', change_user_report_status, name="ChangeReportUserStatus"),

    path('status/detail/<str:slug>/', status_detail_page, name="StatusDetailPage"),
    path('change-status-status/', change_status_status, name="ChangeStatusStatus"),

    path('population-chart/', status_graph, name='population-chart'),
    path('user-chart/', user_graph, name='user_chart'),
    path('status-chart/', status_created_graph, name='status_created_graph'),
]
