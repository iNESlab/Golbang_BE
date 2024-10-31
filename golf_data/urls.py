'''
MVP demo ver 0.0.1
2024.10.31
golf_data/urls.py

역할: golf_data 앱 내의 URL API 엔드포인트 설정
'''

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import GolfCourseViewSet

router = DefaultRouter()
router.register('', GolfCourseViewSet, basename='golfcourse')

urlpatterns = [
    path('', include(router.urls)),
]
