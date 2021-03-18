from django.shortcuts import render, HttpResponseRedirect, HttpResponse, Http404
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from rest_framework.authtoken.models import Token
from django.contrib.sites.shortcuts import get_current_site
from django.utils.encoding import force_bytes, force_text
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.template.loader import render_to_string

from accounts.models import Profile, User
from status.models import Status
from miscellaneous.models import ReportIssue
from friends.models import ReportUsers, Groups, FriendRequest

import string 
import random 
import requests
from samePinch import constants_formats as CustomFileFormats

from datetime import datetime

user_login_required = user_passes_test(lambda user: user.is_server_admin, login_url='/htgt/09/server/admin/login/')
def server_admin_required(view_func):
    decorated_view_func = login_required(user_login_required(view_func), login_url='/htgt/09/server/admin/login/')
    return decorated_view_func

def admin_login(request):
    logout(request)
    email = password = ''
    val=0
    if request.POST:
        email = request.POST['email']
        password = request.POST['password']
        val = 1
        user = authenticate(email=email, password=password)
        obj = User.objects.filter(email=email).first()
        if obj is None:
            val=2
        elif user is None:
            val=4
        elif user.is_server_admin is not True:
            val = 5
        elif user.is_active:
            login(request, user)
            return HttpResponseRedirect('/htgt/09/server/admin/')
        else:
            val=3

    return render(request, 'login_page.html', {'val':val})

@server_admin_required
def admin_home_page(request):
    all_users = Profile.objects.filter(user__is_active=True)

    active_users = list(all_users.filter(user__status='Activated').order_by('-user__signup_time'))
    total_active_users = len(active_users)
    recently_joined_users = active_users[:min(5,total_active_users)]

    total_deactive_users = len(list(all_users.filter(user__status='Deactivated')))

    total_blocked_users = len(list(all_users.filter(user__status='Blocked')))
    total_deleted_users = len(list(all_users.filter(user__status='Deleted')))

    all_status = Status.objects.all()
    active_status = list(all_status.filter(current_status='active').order_by('-created_at'))
    total_active_status = len(active_status)

    rc_status = list(all_status.filter(Q(current_status='active')|Q(current_status='inactive')).order_by('-created_at'))
    recently_created_status = rc_status[:min(5,len(rc_status))]

    total_inactive_status = len(list(all_status.filter(current_status='inactive')))

    total_blocked_status = len(list(all_status.filter(current_status='deleted')))

    all_issues = ReportIssue.objects.all()
    pending_issues = list(all_issues.filter(status='pending').order_by('-reported_on'))
    total_issues_pending = len(pending_issues)
    recent_issues = pending_issues[:min(5,total_issues_pending)]

    total_resolved_issues = len(list(all_issues.filter(status='resolved')))

    total_discarded_issues = len(list(all_issues.filter(status='discarded')))
    
    todays_date = datetime.today().strftime('%Y-%m-%d')
    print(todays_date)
    context = {
        'total_active_users':total_active_users,
        'total_deactive_users':total_deactive_users,
        'total_blocked_users':total_blocked_users,
        'total_deleted_users':total_deleted_users,
        'recently_joined_users':recently_joined_users,

        'total_status':total_inactive_status+total_active_status,
        'total_active_status':total_active_status,
        'total_inactive_status':total_inactive_status,
        'total_blocked_status':total_blocked_status,
        'recently_created_status':recently_created_status,

        'total_issues_pending':total_issues_pending,
        'total_resolved_issues':total_resolved_issues,
        'total_discarded_issues':total_discarded_issues,
        'recent_issues':recent_issues,
        'todays_date': todays_date
    }
    
    return render(request, 'dashboard.html', context)

@server_admin_required
def active_users_view(request):
    active_users = Profile.objects.filter(user__status='Activated').filter(user__is_active=True).order_by('-user__signup_time')
    return render(request, 'active_users.html', {'active_users':active_users})

@server_admin_required
def deactive_users_view(request):
    deactive_users = Profile.objects.filter(user__status='Deactivated').filter(user__is_active=True).order_by('-user__signup_time')
    return render(request, 'deactive_users.html', {'deactive_users':deactive_users})

@server_admin_required
def blocked_users_view(request):
    blocked_users = Profile.objects.filter(user__status='Blocked').filter(user__is_active=True).order_by('-user__signup_time')
    return render(request, 'blocked_users.html', {'blocked_users':blocked_users})

@server_admin_required
def deleted_users_view(request):
    deleted_users = Profile.objects.filter(user__status='Deleted').filter(user__is_active=True).order_by('-user__signup_time')
    return render(request, 'deleted_users.html', {'deleted_users':deleted_users})

@server_admin_required
def reported_users_view(request):
    reported_users = ReportUsers.objects.all().order_by('-reported_on')
    return render(request, 'reported_users.html', {'reported_users':reported_users})

@server_admin_required
def active_status_view(request):
    active_status = Status.objects.filter(current_status='active').order_by('-created_at')
    return render(request, 'active_status.html', {'active_status':active_status})

@server_admin_required
def inactive_status_view(request):
    inactive_status = Status.objects.filter(current_status='inactive').order_by('-created_at')
    return render(request, 'inactive_status.html', {'inactive_status':inactive_status})

@server_admin_required
def deleted_status_view(request):
    deleted_status = Status.objects.filter(current_status='deleted').order_by('-created_at')
    return render(request, 'deleted_status.html', {'deleted_status':deleted_status})

@server_admin_required
def pending_issues_view(request):
    pending_issues = ReportIssue.objects.filter(status='pending').order_by('-reported_on')
    return render(request, 'pending_issues.html', {'pending_issues':pending_issues})

@server_admin_required
def discarded_issues_view(request):
    discarded_issues = ReportIssue.objects.filter(status='discarded').order_by('-reported_on')
    return render(request, 'discarded_issues.html', {'discarded_issues':discarded_issues})

@server_admin_required
def resolved_issues_view(request):
    resolved_issues = ReportIssue.objects.filter(status='resolved').order_by('-reported_on')
    return render(request, 'resolved_issues.html', {'resolved_issues':resolved_issues})

@server_admin_required
def user_detail_page(request, slug):
    profile = get_object_or_404(Profile, slug=slug)
    all_status = Status.objects.filter(author=profile).order_by('-created_at')
    total_reported = len(list(ReportUsers.objects.filter(reported_by=profile)))
    total_status = len(list(all_status))
    return render(request, 'user_detail_page.html', {
                                                        'profile':profile, 
                                                        'all_status':all_status, 
                                                        'total_status':total_status,
                                                        'total_reported':total_reported,
                                                    })

@server_admin_required
def change_user_status(request):
    if request.method == 'POST':
        user_status = request.POST.get('user_status')
        
        user_id = request.POST.get('user_id')
        user_id = int(user_id)
        profile = get_object_or_404(Profile, pk=user_id)
        user = profile.user

        if profile.user.status == user_status:
            url = '/htgt/09/server/admin/user/profile/'+ str(profile.slug)
        
            return HttpResponseRedirect(url)

        if user_status == 'Deleted':
            deleted_suffix = ''.join(random.choices(string.ascii_uppercase +
                            string.digits, k = 4))    
            deleted_suffix = deleted_suffix.join(random.choices(string.ascii_lowercase, k=2))
            deleted_suffix += str(user.pk)
            
            # Status.objects.filter(author=profile).update(current_status='inactive')

            sent_requests = FriendRequest.objects.filter(sender=profile)
            received_requests = FriendRequest.objects.filter(receiver=profile)

            friends_id = []

            for req in sent_requests:
                friends_id.append(req.pk)
            for req in received_requests:
                friends_id.append(req.pk)

            try:
                request_url = CustomFileFormats.NODE_SERVER_DOMAIN + 'user/friendship' 
                node_response = requests.post(
                    request_url,
                    headers={
                        'x-auth-server': CustomFileFormats.NODE_ADMIN_TOKEN,
                        'Content-Type':"application/json",
                    },
                    json={
                        'user': profile.pk,
                        'friends': friends_id
                    }
                )

                node_response.raise_for_status()

            except Exception as e:
                return HttpResponse(str(e))

            received_requests.delete()

            user.username = 'deleted<{}>'.format(deleted_suffix)
            user.status = 'Deleted'
            user.save()
            user.refresh_from_db()

            try:
                current_site = CustomFileFormats.DJANGO_SERVER_DOMAIN
                if profile.avatar:
                    profile_url = str(current_site) + str(profile.avatar.url)
                else:
                    profile_url = ''

                request_url = CustomFileFormats.NODE_SERVER_DOMAIN + 'user/' 
                node_response = requests.post(
                    request_url,
                    headers={
                        'x-auth-server': CustomFileFormats.NODE_ADMIN_TOKEN,
                        'Content-Type':"application/json",
                    },
                    json={
                        'userID': profile.pk,
                        'fullname': profile.full_name,
                        'username': user.username,
                        'profileURL': profile_url
                    }
                )

                node_response.raise_for_status()

            except Exception as e:
                return HttpResponse(str(e))
            
            token = Token.objects.get(user=user).delete()

        elif user_status == 'Blocked':
            Status.objects.filter(author=profile).update(current_status='inactive')

            sent_requests = FriendRequest.objects.filter(sender=profile)
            received_requests = FriendRequest.objects.filter(receiver=profile)

            friends_id = []

            for req in sent_requests:
                friends_id.append(req.pk)
            for req in received_requests:
                friends_id.append(req.pk)

            try:
                request_url = CustomFileFormats.NODE_SERVER_DOMAIN + 'user/friendship' 
                node_response = requests.post(
                    request_url,
                    headers={
                        'x-auth-server': CustomFileFormats.NODE_ADMIN_TOKEN,
                        'Content-Type':"application/json",
                    },
                    json={
                        'user': profile.pk,
                        'friends': friends_id
                    }
                )

                node_response.raise_for_status()

            except Exception as e:
                return HttpResponse(str(e))

            sent_requests.delete()
            received_requests.delete()

            token = Token.objects.get(user=user).delete()

        profile.user.status = user_status
        profile.user.save()
        profile.save()
        
        if user_status == 'Activated':
            try:
                token = Token.objects.get(user=user)
                if token is None:
                    raise Http404
            except:
                Token.objects.create(user=user)

        url = '/htgt/09/server/admin/user/profile/'+ str(profile.slug)
        
        return HttpResponseRedirect(url)

@server_admin_required
def issues_detail_view(request, slug):
    issue = get_object_or_404(ReportIssue, slug=slug)
    return render(request, 'issues_page.html', {'issue':issue})

@server_admin_required
def change_issue_status(request):
    if request.method == 'POST':
        user_status = request.POST.get('issue_status')

        issue_id = request.POST.get('issue_id')
        issue_id = int(issue_id)

        issue = get_object_or_404(ReportIssue, pk=issue_id)
        issue.status = user_status
        issue.save()      

        url = '/htgt/09/server/admin/issues/'+ str(issue.slug)  
        
        return HttpResponseRedirect(url)

@server_admin_required
def report_user_page(request, slug):
    report_us = get_object_or_404(ReportUsers, slug=slug)
    return render(request,'reported_users_detail.html', {'report_us':report_us})

@server_admin_required
def change_user_report_status(request):
    user_issue_id = request.POST.get('user_issue_id')
    report_us = get_object_or_404(ReportUsers, pk=int(user_issue_id))
    issue_select_drop = request.POST.get('issue_status')

    report_us.status = issue_select_drop
    print(issue_select_drop)
    report_us.save()
    report_us.refresh_from_db()
    print(report_us.status, issue_select_drop)

    url = '/htgt/09/server/admin/report/user/'+ str(report_us.slug)  
    return HttpResponseRedirect(url)

@server_admin_required
def status_detail_page(request, slug):
    status = get_object_or_404(Status, slug=slug)
    tp = len(list(Groups.objects.filter(status_id=status)))
    num_hashtags = len(list(status.hashtags.all()))
    todays_date = datetime.today().strftime('%Y-%m-%d')
    print(todays_date)
    return render(request,'status_detail_page.html',{'status':status, 'tp':tp, 'num_hashtags':num_hashtags, "todays_date":todays_date})

@server_admin_required
def change_status_status(request):
    status_id = request.POST.get('status_id')
    status = get_object_or_404(Status, pk=int(status_id))

    try:
        group_leave_request_url = CustomFileFormats.NODE_SERVER_DOMAIN + 'group/leaveGroup/' 
        group_leave_node_response = requests.post(
            group_leave_request_url,
            headers={
                'x-auth-server': CustomFileFormats.NODE_ADMIN_TOKEN,
                'Content-Type':"application/json",
            },
            json={
                'userID': status.author.pk,
                'statusID':status.pk
            }
        )

        group_leave_response = group_leave_node_response.json()
        group_leave_node_response.raise_for_status()

    except Exception as e:
        return HttpResponse(str(e))

    status.current_status = 'deleted'
    status.save()

    url = '/htgt/09/server/admin/status/detail/'+ str(status.slug)  
    return HttpResponseRedirect(url)

from django.http import JsonResponse
from datetime import datetime
from friends.models import Groups
from calendar import monthrange
@server_admin_required
def status_graph(request):
    mon={1:'Jan', 2:'Feb', 3:'Mar', 4:'Apr', 5:'May', 6:'Jun', 7:'Jul', 8:'Aug', 9:'Sep', 10:'Oct', 11:'Nov', 12:'Dec'}
    days={1:31, 2:28, 3:31, 4:30, 5:31, 6:30, 7:31, 8:31, 9:30, 10:31, 11:30, 12:31}
    date=request.GET.get('date')
    date_obj=datetime.strptime(date,"%Y-%m-%d")
    types=request.GET.get('type')
    status=request.GET.get('status')
    d=[]
    if types=='M':
    
        var=Groups.objects.filter(status_id__id=status,created_on__year=date_obj.year)
        print(var)
        k=mon.keys()
        for temp in k:
            d.append(var.filter(created_on__month=str(temp)).count())
        f={
            'labels': list(mon.values()),
            'data': d
            }
        print(f)

        return JsonResponse(data={
            'labels': list(mon.values()),
            'data': d
            })
    else:
        var=Groups.objects.filter(status_id__id=status,created_on__year=date_obj.year,created_on__month=date_obj.month)
        days=monthrange(date_obj.year,date_obj.month)[1]
        data={}
        for i in range(1,days +1):
            data[i]=var.filter(created_on__day=i).count()
        

        return JsonResponse(data={
            'labels': list(data.keys()),
            'data': list(data.values()),
        })


@server_admin_required
def user_graph(request):
    mon={1:'Jan', 2:'Feb', 3:'Mar', 4:'Apr', 5:'May', 6:'Jun', 7:'Jul', 8:'Aug', 9:'Sep', 10:'Oct', 11:'Nov', 12:'Dec'}
    days={1:31, 2:28, 3:31, 4:30, 5:31, 6:30, 7:31, 8:31, 9:30, 10:31, 11:30, 12:31}
    date=request.GET.get('date')
    date_obj=datetime.strptime(date,"%Y-%m-%d")
    types=request.GET.get('type')
    status=request.GET.get('status')
    d=[]
    if types=='M':
    
        var=User.objects.filter(signup_time__year=date_obj.year)
        k=mon.keys()
        for temp in k:
            d.append(var.filter(signup_time__month=str(temp)).count())
        f={
            'labels': list(mon.values()),
            'data': d
            }
        print(f)

        return JsonResponse(data={
            'labels': list(mon.values()),
            'data': d
            })
    else:
        var=User.objects.filter(signup_time__year=date_obj.year,signup_time__month=date_obj.month)
        days=monthrange(date_obj.year,date_obj.month)[1]
        data={}
        for i in range(1,days +1):
            data[i]=var.filter(signup_time__day=i).count()
        

        return JsonResponse(data={
            'labels': list(data.keys()),
            'data': list(data.values()),
        })

@server_admin_required
def status_created_graph(request):
    mon={1:'Jan', 2:'Feb', 3:'Mar', 4:'Apr', 5:'May', 6:'Jun', 7:'Jul', 8:'Aug', 9:'Sep', 10:'Oct', 11:'Nov', 12:'Dec'}
    days={1:31, 2:28, 3:31, 4:30, 5:31, 6:30, 7:31, 8:31, 9:30, 10:31, 11:30, 12:31}
    date=request.GET.get('date')
    date_obj=datetime.strptime(date,"%Y-%m-%d")
    types=request.GET.get('type')
    status=request.GET.get('status')
    d=[]
    if types=='M':
    
        var=Status.objects.filter(created_at__year=date_obj.year)
        k=mon.keys()
        for temp in k:
            d.append(var.filter(created_at__month=str(temp)).count())
        f={
            'labels': list(mon.values()),
            'data': d
            }
        print(f)

        return JsonResponse(data={
            'labels': list(mon.values()),
            'data': d
            })
    else:
        var=Status.objects.filter(created_at__year=date_obj.year,created_at__month=date_obj.month)
        days=monthrange(date_obj.year,date_obj.month)[1]
        data={}
        for i in range(1,days +1):
            data[i]=var.filter(created_at__day=i).count()
        

        return JsonResponse(data={
            'labels': list(data.keys()),
            'data': list(data.values()),
        })


#<input type="date" id="birthday" name="birthday">