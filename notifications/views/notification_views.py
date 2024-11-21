'''
MVP demo ver 0.1.0
2024.11.21
notifications/views/notification_views.py

역할:
- 사용자 알림 관리 API 엔드포인트를 처리합니다.

기능:
1. 알림 히스토리 조회 (GET /notifications/)
2. 알림 읽음 상태 변경 (PATCH /notifications/{notification_id}/)
3. 알림 삭제 (DELETE /notifications/{notification_id}/)
'''

from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.conf import settings
import redis
import json

from utils.error_handlers import handle_404_not_found, handle_400_bad_request, handle_401_unauthorized

# Redis 설정
redis_client = redis.StrictRedis(host=settings.REDIS_HOST, port=settings.REDIS_PORT, db=0)

class NotificationViewSet(viewsets.ViewSet):
    """
    알림 API 뷰셋: 알림 히스토리 조회, 읽음 상태 변경, 삭제
    """
    permission_classes = [IsAuthenticated]  # 사용자 인증 필요

    def list(self, request):
        """
        GET /notifications/
        - 사용자별 알림 히스토리 조회
        - 최근 알림 리스트를 반환한다.
        """
        user_id = request.user.id
        pattern = f"notification:{user_id}:*"  # 사용자별 알림 키 패턴

        try:
            keys = redis_client.keys(pattern)  # Redis에서 해당 키 조회
        except Exception as e:
            # Redis 연결이나 키 검색에서 문제가 발생한 경우
            return handle_400_bad_request(f"Error accessing Redis: {str(e)}")

        # 알림이 없는 경우 404 반환
        if not keys:
            return handle_404_not_found("All Notifications", "")

        # Redis에서 알림 데이터 가져오기
        notifications = []
        for key in keys:
            try:
                notifications.append(json.loads(redis_client.get(key)))
            except Exception as e:
                # 특정 알림 데이터를 처리하지 못했을 경우
                return handle_400_bad_request(f"Error parsing notification: {str(e)}")

        # 성공적으로 알림 데이터를 반환
        return Response({
            "status": 200,
            "message": "Successfully retrieved notification list",
            "data": notifications
        }, status=status.HTTP_200_OK)

    def partial_update(self, request, pk=None):
        """
        PATCH /notifications/{notification_id}/
        - 알림 읽음 상태 변경
        """
        user_id = request.user.id
        notification_key = f"notification:{user_id}:{pk}"  # Redis에서 알림 키 생성

        # 알림 ID가 제공되지 않은 경우
        if not pk:
            return handle_400_bad_request("'notification_id' is required.")

        # Redis에서 알림이 존재하는지 확인
        if not redis_client.exists(notification_key):
            return handle_404_not_found("Notification", pk)

        try:
            # Redis에서 알림 데이터 로드
            notification = json.loads(redis_client.get(notification_key))
            notification['read'] = True  # 읽음 상태로 변경
            redis_client.set(notification_key, json.dumps(notification))  # 변경 사항 저장
        except Exception as e:
            return handle_400_bad_request(f"Error updating notification: {str(e)}")

        return Response({
            "status": 200,
            "message": "Notification read status updated successfully."
        }, status=status.HTTP_200_OK)

    def destroy(self, request, pk=None):
        """
        DELETE /notifications/{notification_id}/
        - 알림 삭제
        """
        user_id = request.user.id
        notification_key = f"notification:{user_id}:{pk}"  # Redis에서 알림 키 생성

        # 알림 ID가 제공되지 않은 경우
        if not pk:
            return handle_400_bad_request("'notification_id' is required.")

        # Redis에서 알림이 존재하는지 확인
        if not redis_client.exists(notification_key):
            return handle_404_not_found("Notification", pk)

        try:
            redis_client.delete(notification_key)  # Redis에서 알림 삭제
        except Exception as e:
            return handle_400_bad_request(f"Error deleting notification: {str(e)}")

        return Response({
            "status": 204,
            "message": "Notification deleted successfully."
        }, status=status.HTTP_204_NO_CONTENT)
