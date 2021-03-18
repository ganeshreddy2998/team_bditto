from django.db.models.signals import post_save,post_delete, pre_save
from django.dispatch import receiver

from .models import Favourites, Liked
from django.core.cache import cache

from friends.models import Groups, BlockedUsers, FriendRequest

from accounts.models import Profile

from .models import Status

@receiver(post_save, sender=Favourites)
def delete_myfavorites_from_cache(sender, instance=None, created=False, **kwargs):
    
    print("clear cache")
    cache.clear()
            
@receiver(post_save, sender=Groups)
def delete_myhistory_from_cache(sender, instance=None, created=False, **kwargs):
    
    print("clear cache")
    cache.clear()
            
            
@receiver(pre_save, sender=Status)
def delete_mystatus_from_cache(sender, instance=None, **kwargs):
    
    print("clear cache")
    cache.clear()
                
                
@receiver(post_save, sender=Liked)
def delete_mylikedstatus_from_cache(sender, instance=None, created=False, **kwargs):
    
    print("clear cache")
    cache.clear()
            
@receiver(post_save, sender=BlockedUsers)
def delete_blockedusers_from_cache(sender, instance=None, created=False, **kwargs):
    
    print("clear cache")
    cache.clear()
            
@receiver(post_save, sender=FriendRequest)
def delete_friendrequests_from_cache(sender, instance=None, created=False, **kwargs):
    
    print("clear cache")
    cache.clear()
            
@receiver(post_delete, sender=FriendRequest)
def delete_friendlist_from_cache(sender, instance=None, *args, **kwargs):
    
    print("clear cache")
    cache.clear()
            
@receiver(post_save, sender=Profile)
def delete_myProfile_from_cache(sender, instance=None, created=False, **kwargs):
    
    print("clear cache")
    cache.clear()
            
@receiver(pre_save, sender=FriendRequest)
def delete_friendlist_from_cache(sender, instance=None, **kwargs):
    
    print("clear cache")
    cache.clear()
            
        