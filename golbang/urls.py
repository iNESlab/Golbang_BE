'''
MVP demo ver 0.0.2
2024.07.25
golbang/urls.py

역할: 골방 프로젝트 전체의 엔드포인트 라우팅
현재 기능:
- admin
- accounts
- club(모임)
'''

from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path('admin/', admin.site.urls),                    # admin 페이지
    path('api/v1/users/', include('accounts.urls')),    # accounts 앱의 URL
    path('api/v1/clubs/', include('clubs.urls')),       # clubs 앱의 URL
    path('auth/', include('drf_social_oauth2.urls', namespace='drf')),
]
