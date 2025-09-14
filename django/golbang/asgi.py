"""
ASGI config for golbang project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.0/howto/deployment/asgi/
"""
import os
import asyncio
import logging

from channels.routing import ProtocolTypeRouter, URLRouter
from django.core.asgi import get_asgi_application

import participants.routing
import chat.routing  # 채팅 라우팅 활성화

# 환경변수 설정
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'golbang.settings')

# Django ASGI 애플리케이션 초기화
django_asgi_app = get_asgi_application()

logger = logging.getLogger(__name__)

# 자동 방송 모니터링 시작 (ASGI 애플리케이션 내에서 처리)

application = ProtocolTypeRouter({
    "http": django_asgi_app,
    "websocket": URLRouter(  # JWTAuthMiddleware 제거 - 채팅용 WebSocket은 인증 없이 허용
        participants.routing.websocket_urlpatterns +  # 기존 라우팅
        chat.routing.websocket_urlpatterns  # 채팅 라우팅 추가
    ),
})
