"""
ASGI config for golbang project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.0/howto/deployment/asgi/
"""
import os

from channels.routing import ProtocolTypeRouter, URLRouter
from django.core.asgi import get_asgi_application
from auth.jwt_auth_middleware import JWTAuthMiddleware

import participants.routing

# 환경변수 설정
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'golbang.settings')

# Django ASGI 애플리케이션 초기화
django_asgi_app = get_asgi_application()

application = ProtocolTypeRouter({
    "http": django_asgi_app,
    "websocket": JWTAuthMiddleware(
        # AllowedHostsOriginValidator( 웹이랑 연결할 때는 사용함
        URLRouter(
            participants.routing.websocket_urlpatterns
        )
        # )
    ),
})
