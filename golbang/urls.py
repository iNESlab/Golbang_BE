'''
MVP demo ver 0.0.1
2024.06.19
golbang/urls.py

역할: 골방 프로젝트 전체의 엔드포인트 라우팅
현재 기능:
- admin
- accounts
'''

from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path('admin/', admin.site.urls),  # admin 페이지
    path('api/user/', include('accounts.urls')),  # accounts 앱의 URL
    path('api/events/', include('events.urls')),
    path('api/club_members/', include('clubMembers.urls')),
    path('api/participants/', include('participants.urls')),
    path('auth/', include('drf_social_oauth2.urls', namespace='drf')),
]
