from rest_framework import serializers
from .models import ChatMessage, ChatNotification, MessageReadStatus, ChatReaction

class ChatMessageSerializer(serializers.ModelSerializer):
    sender_name = serializers.CharField(source='sender.name', read_only=True)
    sender_id = serializers.CharField(source='sender.user_id', read_only=True)
    
    class Meta:
        model = ChatMessage
        fields = [
            'id', 'chat_room', 'sender', 'sender_name', 'sender_id',
            'message_type', 'content', 'is_announcement', 'is_pinned', 'priority',
            'created_at', 'updated_at', 'is_read'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

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
    user_id = serializers.CharField(source='user.user_id', read_only=True)
    
    class Meta:
        model = MessageReadStatus
        fields = ['id', 'message', 'user', 'user_name', 'user_id', 'read_at', 'is_read']
        read_only_fields = ['id', 'read_at']

class ChatReactionSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.name', read_only=True)
    user_id = serializers.CharField(source='user.user_id', read_only=True)
    
    class Meta:
        model = ChatReaction
        fields = ['id', 'message', 'user', 'user_name', 'user_id', 'reaction', 'created_at']
        read_only_fields = ['id', 'created_at']
