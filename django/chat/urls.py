from django.urls import path
from . import views

urlpatterns = [
    # 관리자 메시지 관련
    path('admin-message/', views.send_admin_message, name='send_admin_message'),
    path('announcement/', views.send_announcement, name='send_announcement'),
    
    # 메시지 읽음 표시
    path('mark-read/', views.mark_message_as_read, name='mark_message_as_read'),
    path('mark-all-read/', views.mark_all_messages_as_read, name='mark_all_messages_as_read'),
    path('unread-count/', views.get_unread_count, name='get_unread_count'),
    path('unread-counts/', views.get_all_unread_counts, name='get_all_unread_counts'),
    path('readers/<str:message_id>/', views.get_message_readers, name='get_message_readers'),
    
    # 메시지 고정
    path('toggle-pin/', views.toggle_message_pin, name='toggle_message_pin'),
    path('pinned-messages/', views.get_pinned_messages, name='get_pinned_messages'),
    
    # 메시지 반응
    path('reaction/', views.add_reaction, name='add_reaction'),
    
    # 알림 관련
    path('notifications/', views.get_notifications, name='get_notifications'),
    path('notifications/<str:notification_id>/read/', views.mark_notification_as_read, name='mark_notification_as_read'),
    
    # 🚫 라디오 기능 비활성화 - 안드로이드에서 사용하지 않음
    # path('radio/status/<int:club_id>/', views.get_radio_stream_status, name='get_radio_stream_status'),
    
    # 차단/신고 관련
    path('block-user/', views.block_user, name='block_user'),
    path('unblock-user/', views.unblock_user, name='unblock_user'),
    path('blocked-users/', views.get_blocked_users, name='get_blocked_users'),
    path('clear-blocked-users/', views.clear_all_blocked_users, name='clear_all_blocked_users'),
    path('report-message/', views.report_message, name='report_message'),
    path('check-blocked/<int:user_id>/', views.check_user_blocked, name='check_user_blocked'),
]
