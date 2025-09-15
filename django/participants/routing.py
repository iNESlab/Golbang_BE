# participants/routing.py

from django.urls import path

from auth.jwt_auth_middleware import JWTAuthMiddleware
from participants.stroke import stroke_event_consumers, stroke_group_consumers

websocket_urlpatterns = [
    path('ws/participants/<int:participant_id>/event/stroke', JWTAuthMiddleware(stroke_event_consumers.EventParticipantConsumer.as_asgi())),
    path('ws/participants/<int:participant_id>/group/stroke', JWTAuthMiddleware(stroke_event_consumers.EventParticipantConsumer.as_asgi())),
]