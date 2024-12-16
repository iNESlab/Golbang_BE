'''
MVP demo ver 0.0.2
2024.07.28
clubs/urls.py

역할: clubs 앱 내의 URL API 엔드포인트 설정

'''
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import FeedbackViewSet

router = DefaultRouter()
router.register(r'', FeedbackViewSet,  basename='feedback')

urlpatterns = [
    path('', include(router.urls)),
]
