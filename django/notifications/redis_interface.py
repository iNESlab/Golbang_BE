from golbang import settings
import redis
import json
from asgiref.sync import sync_to_async
from datetime import datetime

# Redis 클라이언트 초기화
redis_client = redis_client = redis.StrictRedis(
    host='redis', 
    port=6379, 
    db=0, 
    password=settings.REDIS_PASSWORD
)


class NotificationRedisInterface:
    """
    Redis와 상호작용하여 알림 데이터를 관리하는 인터페이스
    """

    async def save_notification(self, user_id, notification_id, notification_data, event_id=None, club_id=None):
        """
        Redis에 알림 데이터를 저장합니다.
        """
        print(f"이곳은 save_notification 함수!!!!! user_id={user_id} notification_id={notification_id}, notification_data={notification_data}")

        # 타임스탬프 및 event_id 또는 club_id 데이터 추가
        notification_data.update({
            "timestamp": datetime.now().isoformat(),
            "event_id": event_id,
            "club_id": club_id
        })
        print(f"notification_data에 타임스탬프 추가 => {notification_data}")
        key = f"notification:{user_id}:{notification_id}"
        print(f"Saving notification with key={key} and data={notification_data}")

        await sync_to_async(redis_client.set)(key, json.dumps(notification_data))
        await sync_to_async(redis_client.expire)(key, 604800)  # 7일 후 만료

    async def get_notification(self, user_id, notification_id):
        """
        Redis에서 특정 알림 데이터를 가져옵니다.
        """
        key = f"notification:{user_id}:{notification_id}"
        notification = await sync_to_async(redis_client.get)(key)
        if notification:
            return json.loads(notification)
        return None

    async def delete_notification(self, user_id, notification_id):
        """
        Redis에서 특정 알림 데이터를 삭제합니다.
        """
        key = f"notification:{user_id}:{notification_id}"
        await sync_to_async(redis_client.delete)(key)

    async def get_all_notifications(self, user_id):
        """
        Redis에서 특정 사용자의 모든 알림 데이터를 가져옵니다.
        """
        print(f"get_all_notifications: {user_id} 함수 들어옴")
        pattern = f"notification:{user_id}:*"
        print(f"pattern: {pattern}")

        # 현재 저장된 모든 키 확인 (디버깅용)
        all_keys = await sync_to_async(redis_client.keys)("*")
        print(f"All keys in Redis: {all_keys}")

        # 사용자 관련 키 검색
        keys = await sync_to_async(redis_client.keys)(pattern)
        print(f"Filtered keys: {keys}")

        notifications = []
        for key in keys:
            notification = await sync_to_async(redis_client.get)(key)
            print(f"Fetched notification from key={key}: {notification}")

            if notification:
                print(f"notification 안에 들어옴")
                notifications.append(json.loads(notification))
        return notifications

    async def mark_notification_as_read(self, user_id, notification_id):
        """
        Redis에서 특정 알림을 읽음 상태로 업데이트합니다.
        """
        key = f"notification:{user_id}:{notification_id}"
        notification = await self.get_notification(user_id, notification_id)
        if notification:
            notification["read"] = True
            await self.save_notification(user_id, notification_id, notification)
        else:
            raise ValueError(f"Notification {notification_id} not found for user {user_id}")
