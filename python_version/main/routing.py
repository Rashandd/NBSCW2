from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    # Voice/Text chat: ws://domain/ws/voice/?channel_slug=xxx&channel_type=voice|text
    re_path(r'ws/voice/$', consumers.VoiceChatConsumer.as_asgi()),
    
    # Server presence: ws://domain/ws/presence/?server_slug=xxx (for global voice presence)
    re_path(r'ws/presence/$', consumers.ServerPresenceConsumer.as_asgi()),
    
    # Game: ws://domain/ws/dice-wars/<game_id>/
    re_path(
        r'ws/dice-wars/(?P<game_id>[0-9a-f-]+)/$',
        consumers.GameConsumer_DiceWars.as_asgi()
    ),
]