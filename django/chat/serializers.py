from rest_framework import serializers
from .models import ChatMessage, ChatNotification, MessageReadStatus, ChatReaction, ChatNotificationSettings

class ChatMessageSerializer(serializers.ModelSerializer):
    sender_name = serializers.CharField(source='sender.name', read_only=True)
    sender_id = serializers.CharField(source='sender.id', read_only=True)  # 🔧 수정: 숫자 ID로 변경
    # 🔧 추가: 프로필 이미지 필드
    sender_profile_image = serializers.SerializerMethodField()

    class Meta:
        model = ChatMessage
        fields = [
            'id', 'chat_room', 'sender', 'sender_name', 'sender_id', 'sender_unique_id',
            'sender_profile_image', 'message_type', 'content', 'is_announcement',
            'is_pinned', 'priority', 'created_at', 'updated_at', 'is_read'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_sender_profile_image(self, obj):
        """프로필 이미지 URL 반환 (실시간 우선 - 프로필 변경 즉시 반영)"""
        # 항상 최신 프로필 우선 (실시간 조회)
        if obj.sender and obj.sender.profile_image:
            return obj.sender.profile_image.url

        # 백업: 캐싱된 값 (이미지 없을 때)
        if obj.sender_profile_image:
            return obj.sender_profile_image

        return None

class ChatNotificationSerializer(serializers.ModelSerializer):
    sender_name = serializers.CharField(source='message.sender.name', read_only=True)
    message_content = serializers.CharField(source='message.content', read_only=True)
    
    class Meta:
        model = ChatNotification
        fields = [
            'id', 'user', 'chat_room', 'message', 'sender_name', 'message_content',
            'notification_type', 'title', 'content', 'is_read', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']

class MessageReadStatusSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.name', read_only=True)
    user_id = serializers.CharField(source='user.id', read_only=True)  # 🔧 수정: 숫자 ID로 변경
    
    class Meta:
        model = MessageReadStatus
        fields = ['id', 'message', 'user', 'user_name', 'user_id', 'read_at', 'is_read']
        read_only_fields = ['id', 'read_at']

class ChatReactionSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.name', read_only=True)
    user_id = serializers.CharField(source='user.id', read_only=True)  # 🔧 수정: 숫자 ID로 변경
    
    class Meta:
        model = ChatReaction
        fields = ['id', 'message', 'user', 'user_name', 'user_id', 'reaction', 'created_at']
        read_only_fields = ['id', 'created_at']

class ChatNotificationSettingsSerializer(serializers.ModelSerializer):
    """채팅방 알림 설정 시리얼라이저"""
    chat_room_name = serializers.CharField(source='chat_room.chat_room_name', read_only=True)
    chat_room_type = serializers.CharField(source='chat_room.chat_room_type', read_only=True)
    
    class Meta:
        model = ChatNotificationSettings
        fields = ['id', 'user', 'chat_room', 'chat_room_name', 'chat_room_type', 'is_enabled', 'created_at', 'updated_at']
        read_only_fields = ['id', 'user', 'chat_room', 'created_at', 'updated_at']


