'''
MVP demo ver 0.0.2
2024.07.28
clubs/urls.py

역할: clubs 앱 내의 URL API 엔드포인트 설정

'''
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ClubViewSet, ClubAdminViewSet, ClubMemberViewSet
from .views.club_statistics import ClubStatisticsViewSet

router = DefaultRouter()
router.register(r'', ClubViewSet)
router.register(r'admin', ClubAdminViewSet, basename='club-admin')
router.register(r'', ClubMemberViewSet, basename='club-member')
router.register(r'statistics', ClubStatisticsViewSet, basename='statistics')

urlpatterns = [
    path('', include(router.urls)),
]