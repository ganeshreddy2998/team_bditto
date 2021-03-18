from django.contrib import admin
from .models import Hashtags, Status, StatusFiles, Favourites, Liked

# Hashtags model admin Configuration
@admin.register(Hashtags)
class HashtagsAdmin(admin.ModelAdmin):
    list_display = ('name', 'count', 'created_at', 'last_updated_at')
    ordering = ('last_updated_at',)
    search_fields = ('name',)

# Status model admin Configuration
@admin.register(Status)
class StatusAdmin(admin.ModelAdmin):
    list_display = ('author', 'content', 'background_color', 'current_status', 'created_at', 'last_updated_at')
    ordering = ('last_updated_at',)
    search_fields = ('content', 'author')
    list_filter = ('current_status',)

# StatusFiles model admin Configuration
@admin.register(StatusFiles)
class StatusFilesAdmin(admin.ModelAdmin):
    list_display = ('status', 'file',)

# Favourites model admin Configuration
@admin.register(Favourites)
class FavouritesAdmin(admin.ModelAdmin):
    list_display = ('status', 'set_by', 'set_at')
    ordering = ('set_at',)

# Liked model admin Configuration
@admin.register(Liked)
class LikedAdmin(admin.ModelAdmin):
    list_display = ('status', 'liked_by', 'liked_at')
    ordering = ('liked_at',)



