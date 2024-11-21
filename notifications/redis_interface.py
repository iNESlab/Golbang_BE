import redis
import json
from asgiref.sync import sync_to_async
from datetime import datetime, timedelta

# Redis 클라이언트 초기화
redis_client = redis.StrictRedis(host='redis', port=6379, db=0)


class NotificationRedisInterface:
    """
    Redis와 상호작용하여 알림 데이터를 관리하는 인터페이스
    """

    async def save_notification(self, user_id, notification_id, notification_data):
        """
        Redis에 알림 데이터를 저장합니다.
        :param user_id: 사용자 ID
        :param notification_id: 알림 ID
        :param notification_data: 알림 데이터 (딕셔너리 형태)
        """
        key = f"notification:{user_id}:{notification_id}"
        await sync_to_async(redis_client.set)(key, json.dumps(notification_data))
        await sync_to_async(redis_client.expire)(key, 172800)  # 2일 후 만료 설정

    async def get_notification(self, user_id, notification_id):
        """
        Redis에서 특정 알림 데이터를 가져옵니다.
        :param user_id: 사용자 ID
        :param notification_id: 알림 ID
        :return: 알림 데이터 (딕셔너리 형태)
        """
        key = f"notification:{user_id}:{notification_id}"
        notification = await sync_to_async(redis_client.get)(key)
        if notification:
            return json.loads(notification)
        return None

    async def delete_notification(self, user_id, notification_id):
        """
        Redis에서 특정 알림 데이터를 삭제합니다.
        :param user_id: 사용자 ID
        :param notification_id: 알림 ID
        """
        key = f"notification:{user_id}:{notification_id}"
        await sync_to_async(redis_client.delete)(key)

    async def get_all_notifications(self, user_id):
        """
        Redis에서 특정 사용자의 모든 알림 데이터를 가져옵니다.
        :param user_id: 사용자 ID
        :return: 알림 데이터 리스트
        """
        pattern = f"notification:{user_id}:*"
        keys = await sync_to_async(redis_client.keys)(pattern)
        notifications = []
        for key in keys:
            notification = await sync_to_async(redis_client.get)(key)
            if notification:
                notifications.append(json.loads(notification))
        return notifications

    async def mark_notification_as_read(self, user_id, notification_id):
        """
        Redis에서 특정 알림을 읽음 상태로 업데이트합니다.
        :param user_id: 사용자 ID
        :param notification_id: 알림 ID
        """
        key = f"notification:{user_id}:{notification_id}"
        notification = await self.get_notification(user_id, notification_id)
        if notification:
            notification["read"] = True
            await self.save_notification(user_id, notification_id, notification)
        else:
            raise ValueError(f"Notification {notification_id} not found for user {user_id}")
