from channels.generic.websocket import AsyncJsonWebsocketConsumer

import json
from asgiref.sync import async_to_sync,sync_to_async
import asyncio
from rest_framework.authtoken.models import Token

@sync_to_async
def getusers(token):
    obj=Token.objects.filter(key=token).first()
    if not obj :
        return None 
    else:
        return obj.user.id
class NotificationConsumer(AsyncJsonWebsocketConsumer):

    # async def connect(self):
    #     await self.accept()
    #     await self.channel_layer.group_add("", self.channel_name)
    #     print(f"Added {self.channel_name} channel to gossip")

    # async def disconnect(self, close_code):
    #     await self.channel_layer.group_discard("gossip", self.channel_name)
    #     print(f"Removed {self.channel_name} channel to gossip")
    async def connect(self,*args,**kwargs):
        """
        Called when the websocket is handshaking as part of initial connection.
        """
        try:
            # Pass auth token as a part of url.
            print(self.scope.get('query_string'))
            token = self.scope.get('query_string').decode("utf-8")
            # print(token)
            print("HI")
            # If no token specified, close the connection
            if not token:
                print(1)
                await self.close()
            # Try to authenticate the token from DRF's Token model
            print("HI")
            try:
                print("H")
                obj = await getusers(token)
                if obj:
                    print("token verified")
                else:
                    await self.close()
            except Exception as E:
                print(str(E),1)
                await self.close()


            
            group_name = str(obj)
            print(group_name)
            # Add this channel to the group.

            await self.channel_layer.group_add(
                group_name,
                self.channel_name,
            )
            await self.accept()

        except Exception as e:
            print(str(e),1)
            await self.close()

    async def disconnect(self, code):
        """
        Called when the websocket closes for any reason.
        Leave all the rooms we are still in.
        """
        try:
            # Get auth token from url.
            token = self.scope.get('query_string').decode("utf-8")
            try:
                print("H")
                obj = await getusers(token)
                
            except Exception as E:
                print(str(E),1)
                await self.close()
            # Get the group from which user is to be kicked.
            group_name = str(obj)

            # kick this channel from the group.
            await self.channel_layer.group_discard(group_name, self.channel_name)
        except Exception as e:
            pass

    async def notifi(self, event):
        await self.send_json(event)
        print(f"Got message {event} at {self.channel_name}")
    # async def user_reply(self, event):
    #     await self.send_json(event)
    #     print(f"Got message {event} at {self.channel_name}")
    # async def user_answerlike(self, event):
    #     print("hey")
    #     await self.send_json(event)
    #     print(f"Got message {event} at {self.channel_name}")