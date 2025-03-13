'''
웹소켓을 위한 JWT 인증
'''

import logging

from channels.exceptions import DenyConnection
from channels.middleware import BaseMiddleware
from channels.db import database_sync_to_async
from django.contrib.auth.models import AnonymousUser
from rest_framework_simplejwt.tokens import AccessToken
from django.db import close_old_connections

class JWTAuthMiddleware(BaseMiddleware):
    async def __call__(self, scope, receive, send):
        close_old_connections()

        # 토큰 추출
        token = self.get_token_from_scope(scope)

        # 토큰으로부터 사용자 ID 추출 및 검증
        if token:
            # TODO: user_id -> account_id
            user_id = await self.get_user_from_token(token)
            logging.info(f"User ID: {user_id}")
            if user_id:
                scope['user'] = await self.get_user(user_id)
                logging.info('user %s', scope['user'])

            else:
                scope['user'] = AnonymousUser()  # 유효하지 않은 토큰
                logging.info('AnonymousUser %s', scope['user'])
                raise DenyConnection("INVALID_TOKEN")

        else:
            scope['user'] = AnonymousUser()  # 토큰이 없을 경우
            raise DenyConnection("NOT_FOUND_TOKEN")

        return await super().__call__(scope, receive, send)

    @database_sync_to_async
    def get_user(self, user_id):
        try:
            from accounts.models import User
            return User.objects.get(id=user_id)
        except User.DoesNotExist:
            return AnonymousUser()

    @database_sync_to_async
    def get_user_from_token(self, token):
        try:
            access_token = AccessToken(token)
            return access_token['user_id']
        except Exception:
            raise DenyConnection("NOT_FOUND_USER_FROM_TOKEN")
    def get_token_from_scope(self, scope):
        headers = dict(scope.get("headers", []))
        logging.info('headers: %s', headers)
        auth_header = headers.get(b'authorization', b'').decode('utf-8')
        logging.info('auth_header: %s', auth_header)
        if auth_header.startswith('Bearer '):
            return auth_header.split(' ')[1]

        else:
            return None