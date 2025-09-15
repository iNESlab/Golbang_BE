from django.db import models
from django.conf import settings
from django.utils import timezone
import uuid

class ChatRoom(models.Model):
    CHAT_TYPE_CHOICES = [
        ('EVENT', '이벤트 채팅방'),
        ('CLUB', '클럽 채팅방'),
        ('GLOBAL', '전체 채팅방'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    chat_room_name = models.CharField(max_length=200, verbose_name='채팅방 이름')
    chat_room_type = models.CharField(max_length=20, choices=CHAT_TYPE_CHOICES, verbose_name='채팅방 타입')
    
    # 이벤트 채팅방인 경우
    event_id = models.IntegerField(null=True, blank=True, verbose_name='이벤트 ID')
    
    # 클럽 채팅방인 경우
    club_id = models.IntegerField(null=True, blank=True, verbose_name='클럽 ID')
    
    created_at = models.DateTimeField(default=timezone.now, verbose_name='생성일')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='수정일')
    is_active = models.BooleanField(default=True, verbose_name='활성화 여부')
    
    class Meta:
        db_table = 'chat_rooms'
        verbose_name = '채팅방'
        verbose_name_plural = '채팅방들'
        indexes = [
            models.Index(fields=['chat_room_type', 'event_id']),
            models.Index(fields=['chat_room_type', 'club_id']),
        ]
    
    def __str__(self):
        return f"{self.get_chat_room_type_display()}: {self.chat_room_name}"

class ChatMessage(models.Model):
    MESSAGE_TYPE_CHOICES = [
        ('TEXT', '텍스트'),
        ('IMAGE', '이미지'),
        ('SYSTEM', '시스템 메시지'),
        ('ANNOUNCEMENT', '공지 메시지'),
        ('ADMIN', '관리자 메시지'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    chat_room = models.ForeignKey(ChatRoom, on_delete=models.CASCADE, related_name='messages', verbose_name='채팅방')
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='sent_messages', verbose_name='발신자')
    
    message_type = models.CharField(max_length=20, choices=MESSAGE_TYPE_CHOICES, default='TEXT', verbose_name='메시지 타입')
    content = models.TextField(verbose_name='메시지 내용')
    
    # 🔧 추가: 고도화 필드들
    is_announcement = models.BooleanField(default=False, verbose_name='공지 여부')
    is_pinned = models.BooleanField(default=False, verbose_name='고정 여부')
    priority = models.IntegerField(default=0, verbose_name='우선순위')
    
    created_at = models.DateTimeField(default=timezone.now, verbose_name='전송일')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='수정일')
    is_read = models.BooleanField(default=False, verbose_name='읽음 여부')
    
    class Meta:
        db_table = 'chat_messages'
        verbose_name = '채팅 메시지'
        verbose_name_plural = '채팅 메시지들'
        indexes = [
            models.Index(fields=['chat_room', 'created_at']),
            models.Index(fields=['sender', 'created_at']),
        ]
        ordering = ['created_at']
    
    def __str__(self):
        return f"{self.sender}: {self.content[:50]}"

class ChatRoomParticipant(models.Model):
    ROLE_CHOICES = [
        ('MEMBER', '일반 멤버'),
        ('ADMIN', '관리자'),
        ('MODERATOR', '운영자'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    chat_room = models.ForeignKey(ChatRoom, on_delete=models.CASCADE, related_name='participants', verbose_name='채팅방')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='chat_rooms', verbose_name='사용자')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='MEMBER', verbose_name='역할')
    
    joined_at = models.DateTimeField(default=timezone.now, verbose_name='참여일')
    last_read_at = models.DateTimeField(null=True, blank=True, verbose_name='마지막 읽은 시간')
    is_active = models.BooleanField(default=True, verbose_name='활성화 여부')
    
    class Meta:
        db_table = 'chat_room_participants'
        verbose_name = '채팅방 참가자'
        verbose_name_plural = '채팅방 참가자들'
        unique_together = ['chat_room', 'user']
        indexes = [
            models.Index(fields=['chat_room', 'is_active']),
            models.Index(fields=['user', 'is_active']),
        ]
    
    def __str__(self):
        return f"{self.user.name} in {self.chat_room.chat_room_name}"

class UserBlock(models.Model):
    """사용자 차단 모델"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    blocker = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='blocked_users', verbose_name='차단한 사용자')
    blocked_user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='blocked_by_users', verbose_name='차단된 사용자')
    
    reason = models.CharField(max_length=200, null=True, blank=True, verbose_name='차단 사유')
    created_at = models.DateTimeField(default=timezone.now, verbose_name='차단일')
    is_active = models.BooleanField(default=True, verbose_name='활성 여부')
    
    class Meta:
        db_table = 'user_blocks'
        verbose_name = '사용자 차단'
        verbose_name_plural = '사용자 차단들'
        unique_together = ['blocker', 'blocked_user']
        indexes = [
            models.Index(fields=['blocker', 'is_active']),
            models.Index(fields=['blocked_user', 'is_active']),
        ]
    
    def __str__(self):
        return f"{self.blocker.name} blocked {self.blocked_user.name}"

class ChatReport(models.Model):
    """채팅 신고 모델"""
    REPORT_TYPE_CHOICES = [
        ('SPAM', '스팸 또는 광고'),
        ('ABUSE', '욕설 또는 비하'),
        ('INAPPROPRIATE', '부적절한 내용'),
        ('PRIVACY', '개인정보 유출'),
        ('OTHER', '기타'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    reporter = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='reports_made', verbose_name='신고자')
    reported_user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='reports_received', verbose_name='신고된 사용자')
    reported_message = models.ForeignKey(ChatMessage, on_delete=models.CASCADE, related_name='reports', verbose_name='신고된 메시지')
    
    report_type = models.CharField(max_length=20, choices=REPORT_TYPE_CHOICES, verbose_name='신고 유형')
    reason = models.TextField(verbose_name='신고 사유')
    detail = models.TextField(null=True, blank=True, verbose_name='상세 내용')
    
    status = models.CharField(max_length=20, choices=[
        ('PENDING', '대기중'),
        ('REVIEWING', '검토중'),
        ('RESOLVED', '해결됨'),
        ('DISMISSED', '기각됨'),
    ], default='PENDING', verbose_name='처리 상태')
    
    created_at = models.DateTimeField(default=timezone.now, verbose_name='신고일')
    resolved_at = models.DateTimeField(null=True, blank=True, verbose_name='처리일')
    
    class Meta:
        db_table = 'chat_reports'
        verbose_name = '채팅 신고'
        verbose_name_plural = '채팅 신고들'
        indexes = [
            models.Index(fields=['reported_user', 'status']),
            models.Index(fields=['status', 'created_at']),
        ]
    
    def __str__(self):
        return f"Report by {self.reporter.name} against {self.reported_user.name}"

class ChatConnection(models.Model):
    """WebSocket 연결 상태 추적용 모델"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='chat_connections', verbose_name='사용자')
    chat_room = models.ForeignKey(ChatRoom, on_delete=models.CASCADE, related_name='connections', verbose_name='채팅방')
    
    connection_id = models.CharField(max_length=255, verbose_name='연결 ID')
    ip_address = models.GenericIPAddressField(null=True, blank=True, verbose_name='IP 주소')
    user_agent = models.TextField(null=True, blank=True, verbose_name='사용자 에이전트')
    
    connected_at = models.DateTimeField(default=timezone.now, verbose_name='연결 시간')
    disconnected_at = models.DateTimeField(null=True, blank=True, verbose_name='연결 해제 시간')
    is_active = models.BooleanField(default=True, verbose_name='활성 연결 여부')
    
    class Meta:
        db_table = 'chat_connections'
        verbose_name = '채팅 연결'
        verbose_name_plural = '채팅 연결들'
        indexes = [
            models.Index(fields=['user', 'is_active']),
            models.Index(fields=['chat_room', 'is_active']),
            models.Index(fields=['connected_at']),
        ]
    
    def __str__(self):
        return f"{self.user.name} -> {self.chat_room.chat_room_name}"
    
    def disconnect(self):
        self.disconnected_at = timezone.now()
        self.is_active = False
        self.save()


class MessageReadStatus(models.Model):
    """메시지 읽음 상태 추적"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    message = models.ForeignKey(ChatMessage, on_delete=models.CASCADE, related_name='read_statuses', verbose_name='메시지')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='message_reads', verbose_name='사용자')
    
    read_at = models.DateTimeField(default=timezone.now, verbose_name='읽은 시간')
    is_read = models.BooleanField(default=True, verbose_name='읽음 여부')
    
    class Meta:
        db_table = 'message_read_statuses'
        verbose_name = '메시지 읽음 상태'
        verbose_name_plural = '메시지 읽음 상태들'
        unique_together = ['message', 'user']
        indexes = [
            models.Index(fields=['message', 'is_read']),
            models.Index(fields=['user', 'read_at']),
        ]
    
    def __str__(self):
        return f"{self.user.name} read {self.message.id}"


class ChatNotification(models.Model):
    """채팅 알림"""
    NOTIFICATION_TYPE_CHOICES = [
        ('MESSAGE', '새 메시지'),
        ('ANNOUNCEMENT', '공지사항'),
        ('MENTION', '멘션'),
        ('REACTION', '반응'),
        ('ADMIN', '관리자 메시지'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='chat_notifications', verbose_name='사용자')
    chat_room = models.ForeignKey(ChatRoom, on_delete=models.CASCADE, related_name='notifications', verbose_name='채팅방')
    message = models.ForeignKey(ChatMessage, on_delete=models.CASCADE, related_name='notifications', verbose_name='메시지')
    
    notification_type = models.CharField(max_length=20, choices=NOTIFICATION_TYPE_CHOICES, default='MESSAGE', verbose_name='알림 타입')
    title = models.CharField(max_length=200, verbose_name='알림 제목')
    content = models.TextField(verbose_name='알림 내용')
    
    is_read = models.BooleanField(default=False, verbose_name='읽음 여부')
    created_at = models.DateTimeField(default=timezone.now, verbose_name='생성일')
    
    class Meta:
        db_table = 'chat_notifications'
        verbose_name = '채팅 알림'
        verbose_name_plural = '채팅 알림들'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'is_read']),
            models.Index(fields=['chat_room', 'created_at']),
            models.Index(fields=['notification_type', 'created_at']),
        ]
    
    def __str__(self):
        return f"{self.user.name}: {self.title}"


class ChatReaction(models.Model):
    """메시지 반응 (이모지 반응)"""
    REACTION_CHOICES = [
        ('👍', '좋아요'),
        ('❤️', '하트'),
        ('😂', '웃음'),
        ('😮', '놀람'),
        ('😢', '슬픔'),
        ('😡', '화남'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    message = models.ForeignKey(ChatMessage, on_delete=models.CASCADE, related_name='reactions', verbose_name='메시지')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='message_reactions', verbose_name='사용자')
    reaction = models.CharField(max_length=10, choices=REACTION_CHOICES, verbose_name='반응')
    
    created_at = models.DateTimeField(default=timezone.now, verbose_name='생성일')
    
    class Meta:
        db_table = 'chat_reactions'
        verbose_name = '메시지 반응'
        verbose_name_plural = '메시지 반응들'
        unique_together = ['message', 'user', 'reaction']
        indexes = [
            models.Index(fields=['message', 'reaction']),
            models.Index(fields=['user', 'created_at']),
        ]
    
    def __str__(self):
        return f"{self.user.name} {self.reaction} on {self.message.id}"
