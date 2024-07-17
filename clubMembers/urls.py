'''
MVP demo ver 0.0.3
2024.07.11
clubMembers/urls.py

역할: clubMembers 앱 내의 URL API 엔드포인트 설정
현재 기능:
'''

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ClubMemberViewSet

# end point: api/v1/club-members
router = DefaultRouter()
router.register(r'', ClubMemberViewSet)

urlpatterns = [
    path('', include(router.urls)),
]
