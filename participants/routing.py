from django.urls import path

from participants.socket import event_consumers, group_consumers

websocket_urlpatterns = [
    path('ws/participants/<int:participant_id>/event', event_consumers.EventParticipantConsumer.as_asgi()),
    path('ws/participants/<int:participant_id>/group', group_consumers.GroupParticipantConsumer.as_asgi()),
]