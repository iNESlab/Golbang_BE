'''
MVP demo ver 0.0.2
2024.07.28
clubs/urls.py

역할: clubs 앱 내의 URL API 엔드포인트 설정

'''
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ClubViewSet, ClubAdminViewSet, ClubMemberViewSet

router = DefaultRouter()
router.register(r'', ClubViewSet)
router.register(r'', ClubAdminViewSet, basename='club-admin')
router.register(r'', ClubMemberViewSet, basename='club-member')

urlpatterns = [
    path('', include(router.urls)),
]