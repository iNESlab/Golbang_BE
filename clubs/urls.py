'''
MVP demo ver 0.0.1
2024.07.22
clubs/urls.py

역할: clubs 앱 내의 URL API 엔드포인트 설정

'''
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ClubViewSet

router = DefaultRouter()
router.register(r'', ClubViewSet)

urlpatterns = [
    path('', include(router.urls)),
]