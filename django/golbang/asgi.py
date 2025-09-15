"""
ASGI config for golbang project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.0/howto/deployment/asgi/
"""
import os
import logging

from channels.routing import ProtocolTypeRouter, URLRouter
from django.core.asgi import get_asgi_application
from django.urls import path

from auth.jwt_auth_middleware import JWTAuthMiddleware
import participants.routing
import chat.routing  # 채팅 라우팅 활성화

# 환경변수 설정
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'golbang.settings')

# Django ASGI 애플리케이션 초기화
django_asgi_app = get_asgi_application()

logger = logging.getLogger(__name__)

# participants → JWT 필요
participants_app = JWTAuthMiddleware(
    URLRouter(participants.routing.websocket_urlpatterns)
)
chat_app = URLRouter(chat.routing.websocket_urlpatterns)

# 자동 방송 모니터링 시작 (ASGI 애플리케이션 내에서 처리)

application = ProtocolTypeRouter({
    "http": django_asgi_app,
    "websocket": URLRouter([
        path("ws/participants/", participants_app),  # JWT 필요
        path("ws/chat/", chat_app),                  # 무인증
    ]),
})
