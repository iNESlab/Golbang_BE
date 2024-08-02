'''
MVP demo ver 0.0.8
2024.08.02
events/urls.py

역할: events 앱 내의 URL API 엔드포인트 설정
현재 기능: 이벤트 생성/조회/수정, 핸디캡 자동 매칭
'''
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from events.views.handicap_match_views import HandicapMatchViewSet
from events.views.views import EventViewSet

# end point: api/v1/events/
router = DefaultRouter()
router.register(r'', EventViewSet,'events')
router.register(r'match/handicap', HandicapMatchViewSet, 'handicap_match')
urlpatterns = [
    path('', include(router.urls)),
]