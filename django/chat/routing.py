from django.urls import re_path
from . import consumers
# 🚫 라디오 기능 비활성화 - 안드로이드에서 사용하지 않음
# from .club_radio_consumer import ClubRadioConsumer
# from .synchronized_radio_consumer import SynchronizedRadioConsumer
# from .rtmp_radio_consumer import RTMPRadioConsumer

websocket_urlpatterns = [
    # 이벤트 채팅방: /ws/chat/event_{event_id}/
    re_path(r'ws/chat/event_(?P<room_name>\d+)/$', consumers.ChatConsumer.as_asgi()),
    
    # 클럽 채팅방: /ws/chat/club_{club_id}/
    re_path(r'ws/chat/club_(?P<room_name>\d+)/$', consumers.ChatConsumer.as_asgi()),
    
    # 전체 채팅방: /ws/chat/global/
    re_path(r'ws/chat/global/$', consumers.ChatConsumer.as_asgi()),
    
    # 일반 채팅방: /ws/chat/{room_name}/
    re_path(r'ws/chat/(?P<room_name>\w+)/$', consumers.ChatConsumer.as_asgi()),
    
    # 🚫 라디오 기능 비활성화 - 안드로이드에서 사용하지 않음
    # 🎵 RTMP 라디오 (신규): /ws/rtmp-radio/club/{club_id}/
    # re_path(r'ws/rtmp-radio/club/(?P<club_id>\d+)/$', RTMPRadioConsumer.as_asgi()),
    
    # 🎵 클럽별 라디오 (레거시): /ws/club-radio/club/{club_id}/
    # re_path(r'ws/club-radio/club/(?P<club_id>\d+)/$', ClubRadioConsumer.as_asgi()),
    
    # 🎵 동기화 라디오 (레거시): /ws/synchronized-radio/event/{event_id}/
    # re_path(r'ws/synchronized-radio/event/(?P<event_id>\d+)/$', SynchronizedRadioConsumer.as_asgi()),

    # 🎵 동기화 라디오(클럽 기반, 레거시): /ws/synchronized-radio/club/{club_id}/
    # re_path(r'ws/synchronized-radio/club/(?P<club_id>\d+)/$', SynchronizedRadioConsumer.as_asgi()),
    
]

