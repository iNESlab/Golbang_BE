'''
MVP demo ver 0.0.3
2024.07.11
events/urls.py

역할: events 앱 내의 URL API 엔드포인트 설정
현재 기능:
'''
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import EventViewSet, EventsUpcomingViewSet

# end point: api/v1/events/
router = DefaultRouter()
router.register(r'upcoming', EventsUpcomingViewSet,'upcoming_events')
router.register(r'', EventViewSet,'events')

urlpatterns = [
    path('', include(router.urls)),
]