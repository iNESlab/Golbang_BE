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

from utils.error_handlers import handle_404_not_found, handle_400_bad_request, handle_401_unauthorized
from notifications.redis_interface import NotificationRedisInterface
from asgiref.sync import async_to_sync  # 추가

# Redis 인터페이스 인스턴스 생성
redis_interface = NotificationRedisInterface()

class NotificationViewSet(viewsets.ViewSet):
    """
    알림 API 뷰셋: 알림 히스토리 조회, 읽음 상태 변경, 삭제
    """
    permission_classes = [IsAuthenticated]  # 사용자 인증 필요

    def list(self, request):
        """
        GET /notifications/
        - 사용자별 알림 히스토리 조회
        """
        user_id = request.user.id
        notifications = async_to_sync(redis_interface.get_all_notifications)(user_id)  # async 메서드를 동기 호출
        print(f"===notifications={notifications}")
        if not notifications:
            return handle_404_not_found('Notifications of userId', user_id)

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
        try:
            async_to_sync(redis_interface.mark_notification_as_read)(user_id, pk)  # async 메서드 동기 호출
            return Response({
                "status": 200,
                "message": "Notification read status updated successfully."
            }, status=status.HTTP_200_OK)
        except ValueError as e:
            return handle_404_not_found('Notification', pk)

    def destroy(self, request, pk=None):
        """
        DELETE /notifications/{notification_id}/
        - 알림 삭제
        """
        user_id = request.user.id
        try:
            notification = async_to_sync(redis_interface.get_notification)(user_id, pk)  # async 메서드 동기 호출
            if notification:
                async_to_sync(redis_interface.delete_notification)(user_id, pk)  # async 메서드 동기 호출
                return Response({
                    "status": 204,
                    "message": "Notification deleted successfully."
                }, status=status.HTTP_204_NO_CONTENT)
            else:
                return handle_404_not_found('Notification', pk)
        except Exception as e:
            return handle_400_bad_request(str(e))

