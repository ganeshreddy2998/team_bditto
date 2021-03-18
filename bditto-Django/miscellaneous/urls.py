from django.urls import path,include

from .views import (
                GetCountries, ReportAnyIssue, SearchStatus, SearchUsers
            )

urlpatterns = [
    # Get Countries list
    path('get-countries/', GetCountries.as_view(), name="GetCountries"),

    # report issue
    path('report-issue/', ReportAnyIssue.as_view(), name="ReportAnyIssue",),

    # To search a phrase in status or keyword in status or fullname/username
    path('search-status/', SearchStatus.as_view(), name="SearchStatus"),

    # To search a phrase in status or keyword in status or fullname/username
    path('search-users/', SearchUsers.as_view(), name="SearchUsers"),

]