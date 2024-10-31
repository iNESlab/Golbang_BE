'''
MVP demo ver 0.0.3
2024.08.28
golbang/urls.py

역할: 골방 프로젝트 전체의 엔드포인트 라우팅
현재 기능:
- admin
- accounts, club(모임), event(이벤트), participants(참가자), statistics(통계)
'''

from django.contrib import admin
from django.urls import include, path, re_path
from drf_yasg.views import get_schema_view
from drf_yasg import openapi
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
    path('admin/', admin.site.urls),  # admin 페이지
    path('api/v1/users/', include('accounts.urls')),    # accounts 앱의 URL
    path('api/v1/clubs/', include('clubs.urls')),       # clubs 앱의 URL
    path('api/v1/events/', include('events.urls')),     # events 앱의 URL
    path('api/v1/participants/', include('participants.urls')), # participatns 앱의 URL
    path('api/v1/golfcourses/', include('golf_data.urls')),  # golf_data 앱의 URL

    path('auth/', include('drf_social_oauth2.urls', namespace='drf')),

    # Swagger URL
    re_path(r'^swagger(?P<format>\.json|\.yaml)$', schema_view_v1.without_ui(cache_timeout=0), name='schema-json'),
    re_path(r'^swagger/$', schema_view_v1.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    re_path(r'^redoc/$', schema_view_v1.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
]
