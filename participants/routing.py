from django.urls import path

from participants.stroke import stroke_event_consumers, stroke_group_consumers

websocket_urlpatterns = [
    path('ws/stroke/participants/<int:participant_id>/event/stroke', stroke_event_consumers.EventParticipantConsumer.as_asgi()),
    path('ws/stroke/participants/<int:participant_id>/group/stroke', stroke_group_consumers.GroupParticipantConsumer.as_asgi()),
]