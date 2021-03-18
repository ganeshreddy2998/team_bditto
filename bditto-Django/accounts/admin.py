from django.contrib import admin
from django.contrib.auth.models import Group
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .forms import UserAdminCreationForm, UserAdminChangeForm
from .models import User, Profile

admin.site.unregister(Group)

# User model admin Configuration
class UserAdmin(BaseUserAdmin):
    # The forms to add and change user instances

    form = UserAdminChangeForm
    add_form = UserAdminCreationForm

    # The fields to be used in displaying the User model.
    # These override the definitions on the base UserAdmin
    # that reference specific fields on auth.User.
    list_display = ('email', 'username', 'is_admin', 'status', 'auth_provider')
    list_filter = ('is_admin', 'status', 'is_server_admin')
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Personal info', {'fields': ('username', 'status')}),
        ('Permissions', {'fields': ('is_admin','is_active','is_staff','is_server_admin', 'is_verified')}),
    )
    # add_fieldsets is not a standard ModelAdmin attribute. UserAdmin
    # overrides get_fieldsets to use this attribute when creating a user.
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'username', 'password1', 'password2')}
        ),
    )
    
    search_fields = ('email', 'username',)
    ordering = ('email',)
    filter_horizontal = ()

admin.site.register(User, UserAdmin)


# User Profile model admin Configuration
@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'country', 'city')
    ordering = ('full_name',)
    search_fields = ('full_name', 'country', 'city')
    readonly_fields = ('pk',)
    

# Admin panel branding
admin.site.site_header = 'Bditto'
admin.site.site_title = 'Bditto Admin Portal'
admin.site.index_title = 'Welome to Bditto Administration'
