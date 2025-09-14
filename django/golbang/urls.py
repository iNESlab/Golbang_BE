'''
MVP demo ver 0.0.4
2025.03.28
golbang/urls.py

역할: 골방 프로젝트 전체의 엔드포인트 라우팅
현재 기능:
- admin
- API: accounts, club(모임), event(이벤트), participants(참가자), statistics(통계), golfcourses(골프장 코스 정보), notifications(알림), feedbacks(피드백)
- demo: newperio-calculator
'''

from django.contrib import admin
from django.urls import include, path, re_path
from django.conf import settings
from django.conf.urls.static import static
from drf_yasg.views import get_schema_view
from drf_yasg import openapi
from golbang.views import health_check
from rest_framework.permissions import AllowAny

schema_view_v1 = get_schema_view(
    openapi.Info(
        title="Golbang MVP API",
        default_version='v1',
        description="Golbang MVP API ver1 Swagger",
        # terms_of_service="https://www.google.com/policies/terms/",
        # contact=openapi.Contact(name="test", email="test@test.com"),
        # license=openapi.License(name="Test License"),
    ),
    public=True,
    permission_classes=(AllowAny,),
)

urlpatterns = [
    path('health/', health_check, name='health_check'),
    path('admin/', admin.site.urls),  # admin 페이지
    path('api/v1/users/', include('accounts.urls')),    # accounts 앱의 URL
    path('api/v1/clubs/', include('clubs.urls')),       # clubs 앱의 URL
    path('api/v1/events/', include('events.urls')),     # events 앱의 URL
    path('api/v1/participants/', include('participants.urls')), # participatns 앱의 URL
    path('api/v1/golfcourses/', include('golf_data.urls')),  # golf_data 앱의 URL
    path('api/v1/notifications/', include('notifications.urls')),  # notifications 앱의 URL
    path('api/v1/chat/', include('chat.urls')),  # chat 앱의 URL

    path('api/v1/feedbacks/', include('feedbacks.urls')),  # 사용자 피드백 앱의 URL

    path('calculator/', include('calculator.urls')),     # calculator 앱의 URL

    path('auth/', include('drf_social_oauth2.urls', namespace='drf')),

    # Swagger URL
    re_path(r'^swagger(?P<format>\.json|\.yaml)$', schema_view_v1.without_ui(cache_timeout=0), name='schema-json'),
    re_path(r'^swagger/$', schema_view_v1.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    re_path(r'^redoc/$', schema_view_v1.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
]

# HLS 스트림 파일을 위한 로컬 static 서빙 (개발 환경에서만)
if settings.DEBUG:
    urlpatterns += static('/static/hls/', document_root=settings.BASE_DIR / 'static' / 'hls')
    # 라디오 임시 파일 서빙
    urlpatterns += static('/media/', document_root=settings.MEDIA_ROOT)
