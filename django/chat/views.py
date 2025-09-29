from django.shortcuts import render
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from django.conf import settings
from PIL import Image
import io
import uuid
from .models import ChatRoom, ChatMessage, MessageReadStatus, ChatNotification, ChatReaction
from .serializers import ChatMessageSerializer, ChatNotificationSerializer
# 🚫 라디오 기능 비활성화 - 안드로이드에서 사용하지 않음
# from .services.rtmp_broadcast_service import rtmp_broadcast_service
import json
import asyncio

User = get_user_model()

# Create your views here.

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def send_admin_message(request):
    """관리자 메시지 전송"""
    try:
        content = request.data.get('content', '').strip()
        if not content:
            return Response(
                {'error': '메시지 내용이 필요합니다'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 채팅방 ID 가져오기
        chat_room_id = request.data.get('chat_room_id')
        if not chat_room_id:
            return Response(
                {'error': '채팅방 ID가 필요합니다'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            chat_room = ChatRoom.objects.get(id=chat_room_id)
        except ChatRoom.DoesNotExist:
            return Response(
                {'error': '채팅방을 찾을 수 없습니다'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        # 관리자 권한 확인 - 클럽 채팅방의 경우
        from clubs.models import ClubMember
        
        # 클럽 채팅방인지 확인
        if chat_room.chat_room_type == 'CLUB' and chat_room.club_id:
            # 클럽 채팅방의 경우 클럽 관리자 권한 확인
            try:
                from clubs.models import Club
                club = Club.objects.get(id=chat_room.club_id)
                club_member = ClubMember.objects.get(user=request.user, club=club)
                if club_member.role != "admin":
                    return Response(
                        {'error': '관리자 권한이 필요합니다'}, 
                        status=status.HTTP_403_FORBIDDEN
                    )
            except (Club.DoesNotExist, ClubMember.DoesNotExist):
                return Response(
                    {'error': '관리자 권한이 필요합니다'}, 
                    status=status.HTTP_403_FORBIDDEN
                )
        else:
            # 일반 채팅방의 경우 기존 방식 사용
            from .models import ChatRoomParticipant
            participant = ChatRoomParticipant.objects.filter(
                chat_room=chat_room,
                user=request.user,
                is_active=True
            ).first()
            
            if not participant or participant.role not in ['ADMIN', 'MODERATOR']:
                return Response(
                    {'error': '관리자 권한이 필요합니다'}, 
                    status=status.HTTP_403_FORBIDDEN
                )
        
        # 관리자 메시지 생성
        message = ChatMessage.objects.create(
            chat_room=chat_room,
            sender=request.user,
            content=content,
            message_type='ADMIN',
            is_announcement=False,
            is_pinned=False,
            priority=0
        )
        
        # 알림 생성
        _create_notifications_for_message(message, 'ADMIN')
        
        return Response({
            'message': '관리자 메시지가 전송되었습니다',
            'message_id': str(message.id)
        }, status=status.HTTP_201_CREATED)
        
    except Exception as e:
        return Response(
            {'error': f'서버 오류: {str(e)}'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def send_announcement(request):
    """공지 메시지 전송"""
    try:
        content = request.data.get('content', '').strip()
        is_pinned = request.data.get('is_pinned', False)
        priority = request.data.get('priority', 0)
        
        if not content:
            return Response(
                {'error': '메시지 내용이 필요합니다'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 채팅방 ID 가져오기
        chat_room_id = request.data.get('chat_room_id')
        if not chat_room_id:
            return Response(
                {'error': '채팅방 ID가 필요합니다'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            chat_room = ChatRoom.objects.get(id=chat_room_id)
        except ChatRoom.DoesNotExist:
            return Response(
                {'error': '채팅방을 찾을 수 없습니다'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        # 관리자 권한 확인
        from .models import ChatRoomParticipant
        participant = ChatRoomParticipant.objects.filter(
            chat_room=chat_room,
            user=request.user,
            is_active=True
        ).first()
        
        if not participant or participant.role not in ['ADMIN', 'MODERATOR']:
            return Response(
                {'error': '관리자 권한이 필요합니다'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        # 공지 메시지 생성
        message = ChatMessage.objects.create(
            chat_room=chat_room,
            sender=request.user,
            content=content,
            message_type='ANNOUNCEMENT',
            is_announcement=True,
            is_pinned=is_pinned,
            priority=priority
        )
        
        # 알림 생성
        _create_notifications_for_message(message, 'ANNOUNCEMENT')
        
        return Response({
            'message': '공지 메시지가 전송되었습니다',
            'message_id': str(message.id)
        }, status=status.HTTP_201_CREATED)
        
    except Exception as e:
        return Response(
            {'error': f'서버 오류: {str(e)}'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def mark_message_as_read(request):
    """메시지 읽음 표시"""
    try:
        message_id = request.data.get('message_id')
        if not message_id:
            return Response(
                {'error': '메시지 ID가 필요합니다'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            message = ChatMessage.objects.get(id=message_id)
        except ChatMessage.DoesNotExist:
            return Response(
                {'error': '메시지를 찾을 수 없습니다'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        # 읽음 상태 생성/업데이트
        read_status, created = MessageReadStatus.objects.get_or_create(
            message=message,
            user=request.user,
            defaults={'is_read': True}
        )
        
        if not created:
            read_status.is_read = True
            read_status.read_at = timezone.now()
            read_status.save()
        
        # 읽은 사람 수 조회
        read_count = MessageReadStatus.objects.filter(
            message=message,
            is_read=True
        ).count()
        
        return Response({
            'message': '읽음 표시가 완료되었습니다',
            'read_count': read_count
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response(
            {'error': f'서버 오류: {str(e)}'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def add_reaction(request):
    """메시지 반응 추가"""
    try:
        message_id = request.data.get('message_id')
        reaction = request.data.get('reaction')
        
        if not message_id or not reaction:
            return Response(
                {'error': '메시지 ID와 반응이 필요합니다'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            message = ChatMessage.objects.get(id=message_id)
        except ChatMessage.DoesNotExist:
            return Response(
                {'error': '메시지를 찾을 수 없습니다'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        # 반응 생성/업데이트
        reaction_obj, created = ChatReaction.objects.get_or_create(
            message=message,
            user=request.user,
            reaction=reaction
        )
        
        # 반응 수 조회
        from django.db.models import Count
        reactions = ChatReaction.objects.filter(message=message).values('reaction').annotate(count=Count('reaction'))
        reaction_counts = {item['reaction']: item['count'] for item in reactions}
        
        return Response({
            'message': '반응이 추가되었습니다',
            'reaction_counts': reaction_counts
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response(
            {'error': f'서버 오류: {str(e)}'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_notifications(request):
    """알림 목록 조회"""
    try:
        notifications = ChatNotification.objects.filter(
            user=request.user,
            is_read=False
        ).order_by('-created_at')[:50]
        
        serializer = ChatNotificationSerializer(notifications, many=True)
        
        return Response({
            'notifications': serializer.data,
            'count': notifications.count()
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response(
            {'error': f'서버 오류: {str(e)}'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def mark_notification_as_read(request, notification_id):
    """알림 읽음 표시"""
    try:
        try:
            notification = ChatNotification.objects.get(
                id=notification_id,
                user=request.user
            )
        except ChatNotification.DoesNotExist:
            return Response(
                {'error': '알림을 찾을 수 없습니다'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        notification.is_read = True
        notification.save()
        
        return Response({
            'message': '알림이 읽음 처리되었습니다'
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response(
            {'error': f'서버 오류: {str(e)}'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_message_readers(request, message_id):
    """메시지를 읽은 사람 목록 조회"""
    try:
        try:
            message = ChatMessage.objects.get(id=message_id)
        except ChatMessage.DoesNotExist:
            return Response(
                {'error': '메시지를 찾을 수 없습니다'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        readers = MessageReadStatus.objects.filter(
            message=message,
            is_read=True
        ).select_related('user')
        
        reader_list = []
        for read_status in readers:
            reader_list.append({
                'user_id': str(read_status.user.user_id),
                'user_name': read_status.user.name,
                'read_at': read_status.read_at.isoformat()
            })
        
        return Response({
            'readers': reader_list,
            'count': len(reader_list)
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response(
            {'error': f'서버 오류: {str(e)}'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

def _create_notifications_for_message(message, notification_type):
    """메시지에 대한 알림 생성"""
    try:
        # 채팅방 참가자들에게 알림 생성
        from .models import ChatRoomParticipant
        participants = ChatRoomParticipant.objects.filter(
            chat_room=message.chat_room,
            is_active=True
        ).exclude(user=message.sender)  # 발신자 제외
        
        for participant in participants:
            title = f"{message.sender.name}님이 메시지를 보냈습니다"
            if notification_type == 'ANNOUNCEMENT':
                title = f"📢 공지사항: {message.sender.name}"
            elif notification_type == 'ADMIN':
                title = f"👑 관리자 메시지: {message.sender.name}"
            
            ChatNotification.objects.create(
                user=participant.user,
                chat_room=message.chat_room,
                message=message,
                notification_type=notification_type,
                title=title,
                content=message.content[:100]
            )
    except Exception as e:
        print(f"알림 생성 실패: {e}")

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def mark_message_as_read(request):
    """메시지 읽음 상태 업데이트"""
    try:
        message_id = request.data.get('message_id')
        if not message_id:
            return Response(
                {'error': '메시지 ID가 필요합니다'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            message = ChatMessage.objects.get(id=message_id)
        except ChatMessage.DoesNotExist:
            return Response(
                {'error': '메시지를 찾을 수 없습니다'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        # 읽음 상태 생성 또는 업데이트
        read_status, created = MessageReadStatus.objects.get_or_create(
            user=request.user,
            message=message,
            defaults={'read_at': timezone.now()}
        )
        
        if not created:
            read_status.read_at = timezone.now()
            read_status.save()
        
        return Response({
            'success': True,
            'message_id': message_id,
            'read_at': read_status.read_at.isoformat()
        })
        
    except Exception as e:
        return Response(
            {'error': f'읽음 상태 업데이트 실패: {str(e)}'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def mark_all_messages_as_read(request):
    """채팅방의 모든 메시지 읽음 상태 업데이트"""
    try:
        chat_room_id = request.data.get('chat_room_id')
        if not chat_room_id:
            return Response(
                {'error': '채팅방 ID가 필요합니다'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # 클럽 ID로 채팅방 찾기
            try:
                club_id = int(chat_room_id)
                chat_room = ChatRoom.objects.get(
                    chat_room_type='CLUB',
                    club_id=club_id
                )
                print(f"🔍 클럽 ID {club_id}로 채팅방 찾음: {chat_room.id}")
            except ValueError:
                # UUID 형식으로 채팅방 찾기 시도
                chat_room = ChatRoom.objects.get(id=chat_room_id)
                print(f"🔍 UUID {chat_room_id}로 채팅방 찾음: {chat_room.id}")
        except ChatRoom.DoesNotExist:
            return Response(
                {'error': '채팅방을 찾을 수 없습니다'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        # 해당 채팅방의 모든 메시지에 대해 읽음 상태 업데이트
        messages = ChatMessage.objects.filter(chat_room=chat_room)
        read_count = 0
        
        for message in messages:
            read_status, created = MessageReadStatus.objects.get_or_create(
                user=request.user,
                message=message,
                defaults={'read_at': timezone.now()}
            )
            
            if not created:
                read_status.read_at = timezone.now()
                read_status.save()
            
            read_count += 1
        
        return Response({
            'success': True,
            'chat_room_id': chat_room_id,
            'read_count': read_count
        })
        
    except Exception as e:
        return Response(
            {'error': f'읽음 상태 업데이트 실패: {str(e)}'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_unread_count(request):
    """채팅방별 안읽은 메시지 개수 조회"""
    try:
        chat_room_id = request.GET.get('chat_room_id')
        if not chat_room_id:
            return Response(
                {'error': '채팅방 ID가 필요합니다'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # 클럽 ID로 채팅방 찾기
            try:
                club_id = int(chat_room_id)
                chat_room = ChatRoom.objects.get(
                    chat_room_type='CLUB',
                    club_id=club_id
                )
                print(f"🔍 클럽 ID {club_id}로 채팅방 찾음: {chat_room.id}")
            except ValueError:
                # UUID 형식으로 채팅방 찾기 시도
                chat_room = ChatRoom.objects.get(id=chat_room_id)
                print(f"🔍 UUID {chat_room_id}로 채팅방 찾음: {chat_room.id}")
        except ChatRoom.DoesNotExist:
            return Response(
                {'error': '채팅방을 찾을 수 없습니다'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        # 해당 채팅방의 모든 메시지 중 읽지 않은 메시지 개수 계산 (자신이 보낸 메시지 제외)
        unread_count = ChatMessage.objects.filter(
            chat_room=chat_room
        ).exclude(
            sender=request.user  # 🔧 수정: 자신이 보낸 메시지 제외
        ).exclude(
            read_statuses__user=request.user  # 읽음 상태가 있는 메시지 제외
        ).count()
        
        print(f"🔍 채팅방 {chat_room_id}의 안읽은 메시지 개수: {unread_count}")
        
        return Response({
            'success': True,
            'chat_room_id': chat_room_id,
            'unread_count': unread_count
        })
        
    except Exception as e:
        return Response(
            {'error': f'안읽은 메시지 개수 조회 실패: {str(e)}'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def toggle_message_pin(request):
    """메시지 고정/해제"""
    try:
        message_id = request.data.get('message_id')
        if not message_id:
            return Response(
                {'error': '메시지 ID가 필요합니다'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # UUID 형태가 아닌 경우 (관리자 메시지 등) 처리
            import uuid
            try:
                # UUID 형태인지 확인
                uuid.UUID(str(message_id))
                message = ChatMessage.objects.get(id=message_id)
            except ValueError:
                # UUID가 아닌 경우, 다른 방법으로 찾기 (예: 타임스탬프 기반)
                print(f"⚠️ UUID가 아닌 메시지 ID: {message_id}")
                return Response(
                    {'error': f'유효하지 않은 메시지 ID 형식입니다: {message_id}'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
        except ChatMessage.DoesNotExist:
            return Response(
                {'error': '메시지를 찾을 수 없습니다'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        # 관리자 권한 확인 - 클럽 채팅방의 경우
        from clubs.models import ClubMember
        
        print(f"🔍 메시지 고정 권한 확인: 사용자={request.user.user_id}, 채팅방={message.chat_room.id}")
        
        # 클럽 채팅방인지 확인
        if message.chat_room.chat_room_type == 'CLUB' and message.chat_room.club_id:
            print(f"🔍 클럽 채팅방 확인: 클럽 ID={message.chat_room.club_id}")
            # 클럽 채팅방의 경우 클럽 관리자 권한 확인
            try:
                from clubs.models import Club
                club = Club.objects.get(id=message.chat_room.club_id)
                club_member = ClubMember.objects.get(user=request.user, club=club)
                print(f"🔍 클럽 멤버 확인: role={club_member.role}")
                if club_member.role != "admin":
                    print("❌ 클럽 관리자가 아님")
                    return Response(
                        {'error': '관리자 권한이 필요합니다'}, 
                        status=status.HTTP_403_FORBIDDEN
                    )
                print("✅ 클럽 관리자 권한 확인됨")
            except (Club.DoesNotExist, ClubMember.DoesNotExist):
                print("❌ 클럽 또는 클럽 멤버가 아님")
                return Response(
                    {'error': '관리자 권한이 필요합니다'}, 
                    status=status.HTTP_403_FORBIDDEN
                )
        else:
            print("🔍 일반 채팅방 확인")
            # 일반 채팅방의 경우 기존 방식 사용
            from .models import ChatRoomParticipant
            participant = ChatRoomParticipant.objects.filter(
                chat_room=message.chat_room,
                user=request.user,
                is_active=True
            ).first()
            
            if not participant or participant.role not in ['ADMIN', 'MODERATOR']:
                print(f"❌ 일반 채팅방 권한 없음: participant={participant}")
                return Response(
                    {'error': '관리자 권한이 필요합니다'}, 
                    status=status.HTTP_403_FORBIDDEN
                )
            print("✅ 일반 채팅방 권한 확인됨")
        
        # 고정 상태 토글
        if not message.is_pinned:
            # 새로운 메시지를 고정할 때, 기존 고정된 메시지들 해제
            ChatMessage.objects.filter(
                chat_room=message.chat_room,
                is_pinned=True
            ).update(is_pinned=False)
            message.is_pinned = True
        else:
            # 이미 고정된 메시지를 해제
            message.is_pinned = False
        
        message.save()
        
        return Response({
            'success': True,
            'message_id': message_id,
            'is_pinned': message.is_pinned,
            'message': f'메시지가 {"고정" if message.is_pinned else "고정 해제"}되었습니다'
        })
        
    except Exception as e:
        return Response(
            {'error': f'메시지 고정/해제 실패: {str(e)}'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_all_unread_counts(request):
    """사용자의 모든 채팅방 안읽은 메시지 개수 조회"""
    try:
        # 사용자가 참여한 모든 채팅방 조회
        user_chat_rooms = ChatRoom.objects.filter(
            participants__user=request.user
        ).distinct()
        
        unread_counts = {}
        for chat_room in user_chat_rooms:
            unread_count = ChatMessage.objects.filter(
                chat_room=chat_room
            ).exclude(
                sender=request.user  # 🔧 수정: 자신이 보낸 메시지 제외
            ).exclude(
                messagereadstatus__user=request.user  # 읽음 상태가 있는 메시지 제외
            ).count()
            
            if unread_count > 0:
                unread_counts[str(chat_room.id)] = unread_count
        
        return Response({
            'success': True,
            'unread_counts': unread_counts
        })
        
    except Exception as e:
        return Response(
            {'error': f'안읽은 메시지 개수 조회 실패: {str(e)}'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

# 🚫 라디오 기능 비활성화 - 안드로이드에서 사용하지 않음
"""
@api_view(['GET'])
@permission_classes([AllowAny])  # 라디오 상태는 누구나 확인 가능
def get_radio_stream_status(request, club_id):
    \"\"\"클럽 라디오 스트림 상태 확인\"\"\"
    try:
        # 비동기 함수를 동기적으로 호출
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            broadcast_status = loop.run_until_complete(
                rtmp_broadcast_service.get_broadcast_status(club_id)
            )
        finally:
            loop.close()
        
        # 현재 활성 스트림 URL 결정
        import os
        
        # 실제 HLS 파일 존재 여부 확인 (nginx-rtmp 컨테이너의 /var/hls 확인)
        # Docker 볼륨 마운트를 통해 접근 가능한 경로 확인
        import subprocess
        
        def check_stream_active(stream_name):
            try:
                import requests
                # Docker 네트워크에서는 nginx-rtmp 컨테이너명 사용
                response = requests.get('http://nginx-rtmp/stat', timeout=5)
                if response.status_code == 200:
                    return f'<name>{stream_name}</name>' in response.text
                return False
            except Exception as e:
                # 디버깅용 로그
                print(f"❌ 스트림 상태 확인 오류: {e}")
                return False
        
        current_stream = None
        
        # 해설 스트림이 있으면 우선
        if check_stream_active(f"club_{club_id}_commentary"):
            current_stream = f"http://localhost/hls/club_{club_id}_commentary/index.m3u8"
        # 기본 스트림이 있으면 사용
        elif check_stream_active(f"club_{club_id}"):
            current_stream = f"http://localhost/hls/club_{club_id}/index.m3u8"
        
        # 실제 파일 존재 여부로 active 상태 결정
        actual_active = current_stream is not None
        
        return Response({
            'success': True,
            'club_id': club_id,
            'active': actual_active,
            'broadcast_service_active': broadcast_status['active'],  # 디버깅용
            'current_stream_url': current_stream,
            'timestamp': timezone.now().isoformat()
        })
        
    except Exception as e:
        return Response(
            {'error': f'라디오 스트림 상태 조회 실패: {str(e)}'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
"""

# 차단/신고 관련 API
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def block_user(request):
    """사용자 차단"""
    try:
        from .models import UserBlock
        
        blocked_user_id = request.data.get('blocked_user_id')
        reason = request.data.get('reason', '')
        
        if not blocked_user_id:
            return Response(
                {'error': '차단할 사용자 ID가 필요합니다'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # senderId는 user_id (문자열)이므로 user_id로 조회
            blocked_user = User.objects.get(user_id=blocked_user_id)
        except User.DoesNotExist:
            return Response(
                {'error': '차단할 사용자를 찾을 수 없습니다'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        # 자기 자신 차단 방지
        if blocked_user.id == request.user.id:
            return Response(
                {'error': '자기 자신을 차단할 수 없습니다'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 이미 차단된 사용자인지 확인 (활성/비활성 모두 검사)
        existing_block = UserBlock.objects.filter(
            blocker=request.user,
            blocked_user=blocked_user,
        ).first()
        
        if existing_block:
            if existing_block.is_active:
                # 이미 활성 상태로 차단되어 있음
                return Response(
                    {'error': '이미 차단된 사용자입니다'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            # 과거에 차단했다가 해제한 기록 -> 재활성화
            existing_block.is_active = True
            existing_block.reason = reason
            existing_block.save(update_fields=['is_active', 'reason'])
            return Response(
                {
                    'message': f'{blocked_user.name}님을 다시 차단했습니다',
                    'block_id': str(existing_block.id)
                },
                status=status.HTTP_200_OK
            )
        
        # 차단 생성
        block = UserBlock.objects.create(
            blocker=request.user,
            blocked_user=blocked_user,
            reason=reason
        )
        
        return Response({
            'message': f'{blocked_user.name}님을 차단했습니다',
            'block_id': str(block.id)
        }, status=status.HTTP_201_CREATED)
        
    except Exception as e:
        return Response(
            {'error': f'사용자 차단 실패: {str(e)}'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def unblock_user(request):
    """사용자 차단 해제"""
    try:
        from .models import UserBlock
        
        blocked_user_id = request.data.get('blocked_user_id')
        
        if not blocked_user_id:
            return Response(
                {'error': '차단 해제할 사용자 ID가 필요합니다'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # senderId는 user_id (문자열)이므로 user_id로 조회
            blocked_user = User.objects.get(user_id=blocked_user_id)
        except User.DoesNotExist:
            return Response(
                {'error': '차단 해제할 사용자를 찾을 수 없습니다'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        # 차단 기록 찾기
        block = UserBlock.objects.filter(
            blocker=request.user,
            blocked_user=blocked_user,
            is_active=True
        ).first()
        
        if not block:
            return Response(
                {'error': '차단되지 않은 사용자입니다'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 차단 해제
        block.is_active = False
        block.save()
        
        return Response({
            'message': f'{blocked_user.name}님의 차단을 해제했습니다'
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response(
            {'error': f'차단 해제 실패: {str(e)}'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_blocked_users(request):
    """차단된 사용자 목록 조회"""
    try:
        from .models import UserBlock
        
        blocked_users = UserBlock.objects.filter(
            blocker=request.user,
            is_active=True
        ).select_related('blocked_user')
        
        blocked_list = []
        for block in blocked_users:
            blocked_list.append({
                'user_id': block.blocked_user.user_id,  # user_id 필드 사용
                'user_name': block.blocked_user.name,
                'reason': block.reason,
                'blocked_at': block.created_at.isoformat()
            })
        
        return Response({
            'blocked_users': blocked_list
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response(
            {'error': f'차단된 사용자 목록 조회 실패: {str(e)}'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def clear_all_blocked_users(request):
    """모든 차단된 사용자 해제 (개발/테스트용)"""
    try:
        from .models import UserBlock
        
        # 현재 사용자가 차단한 모든 사용자 해제
        blocked_count = UserBlock.objects.filter(
            blocker=request.user,
            is_active=True
        ).update(is_active=False)
        
        return Response({
            'message': f'{blocked_count}명의 차단을 모두 해제했습니다'
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response(
            {'error': f'전체 차단 해제 실패: {str(e)}'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def report_message(request):
    """메시지 신고"""
    try:
        from .models import ChatReport
        
        message_id = request.data.get('message_id')
        report_type = request.data.get('report_type')
        reason = request.data.get('reason', '')
        detail = request.data.get('detail', '')
        
        if not message_id or not report_type:
            return Response(
                {'error': '메시지 ID와 신고 유형이 필요합니다'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            message = ChatMessage.objects.get(id=message_id)
        except ChatMessage.DoesNotExist:
            return Response(
                {'error': '신고할 메시지를 찾을 수 없습니다'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        # 자기 자신의 메시지 신고 방지
        if message.sender.id == request.user.id:
            return Response(
                {'error': '자기 자신의 메시지를 신고할 수 없습니다'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 신고 생성
        report = ChatReport.objects.create(
            reporter=request.user,
            reported_user=message.sender,
            reported_message=message,
            report_type=report_type,
            reason=reason,
            detail=detail
        )
        
        return Response({
            'message': '신고가 접수되었습니다',
            'report_id': str(report.id)
        }, status=status.HTTP_201_CREATED)
        
    except Exception as e:
        return Response(
            {'error': f'메시지 신고 실패: {str(e)}'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def check_user_blocked(request, user_id):
    """특정 사용자가 차단되었는지 확인"""
    try:
        from .models import UserBlock
        
        is_blocked = UserBlock.objects.filter(
            blocker=request.user,
            blocked_user__user_id=user_id,
            is_active=True
        ).exists()
        
        return Response({
            'is_blocked': is_blocked
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response(
            {'error': f'차단 상태 확인 실패: {str(e)}'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_pinned_messages(request):
    """고정된 메시지 목록 조회"""
    try:
        chat_room_id = request.query_params.get('chat_room_id')
        if not chat_room_id:
            return Response(
                {'error': '채팅방 ID가 필요합니다'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # 클럽 ID로 채팅방 찾기
            try:
                club_id = int(chat_room_id)
                chat_room = ChatRoom.objects.get(
                    chat_room_type='CLUB',
                    club_id=club_id
                )
                print(f"🔍 클럽 ID {club_id}로 채팅방 찾음: {chat_room.id}")
            except ValueError:
                # UUID 형식으로 채팅방 찾기 시도
                chat_room = ChatRoom.objects.get(id=chat_room_id)
                print(f"🔍 UUID {chat_room_id}로 채팅방 찾음: {chat_room.id}")
        except ChatRoom.DoesNotExist:
            return Response(
                {'error': '채팅방을 찾을 수 없습니다'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        # 고정된 메시지 조회 (하나만)
        pinned_messages = ChatMessage.objects.filter(
            chat_room=chat_room,
            is_pinned=True
        ).order_by('-created_at')[:1]  # 최신 고정된 메시지 하나만
        
        messages_data = []
        for message in pinned_messages:
            messages_data.append({
                'id': str(message.id),
                'content': message.content,
                'sender': message.sender.name,
                'sender_id': message.sender.user_id,
                'message_type': message.message_type,
                'created_at': message.created_at.isoformat(),
                'is_pinned': message.is_pinned,
            })
        
        return Response({
            'success': True,
            'messages': messages_data
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response(
            {'error': f'고정된 메시지 조회 실패: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def upload_chat_image(request):
    """채팅 이미지 업로드"""
    try:
        # 이미지 파일 확인
        if 'image' not in request.FILES:
            return Response(
                {'error': '이미지 파일이 필요합니다'},
                status=status.HTTP_400_BAD_REQUEST
            )

        image_file = request.FILES['image']

        # 파일 타입 검증
        allowed_types = ['image/jpeg', 'image/png', 'image/gif', 'image/webp']
        if image_file.content_type not in allowed_types:
            return Response(
                {'error': '지원하지 않는 이미지 형식입니다 (JPEG, PNG, GIF, WebP만 허용)'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 파일 크기 제한 (10MB)
        max_size = 10 * 1024 * 1024  # 10MB
        if image_file.size > max_size:
            return Response(
                {'error': '이미지 파일이 너무 큽니다 (최대 10MB)'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 고유한 파일명 생성
        file_extension = image_file.name.split('.')[-1].lower()
        unique_filename = f"{uuid.uuid4()}.{file_extension}"

        # S3에 업로드할 경로
        s3_path = f"chat_images/{unique_filename}"

        # PIL을 사용하여 이미지 처리 및 압축
        try:
            image = Image.open(image_file)

            # EXIF 회전 정보 적용 (JPEG의 경우)
            if hasattr(image, '_getexif') and image._getexif():
                from PIL import ImageOps
                image = ImageOps.exif_transpose(image)

            # 이미지 리사이징 (최대 1920x1080, 화질 유지)
            max_width, max_height = 1920, 1080
            if image.width > max_width or image.height > max_height:
                image.thumbnail((max_width, max_height), Image.Resampling.LANCZOS)

            # 메모리에 저장
            output = io.BytesIO()
            if image_file.content_type == 'image/jpeg':
                image.save(output, format='JPEG', quality=85, optimize=True)
            elif image_file.content_type == 'image/png':
                image.save(output, format='PNG', optimize=True)
            elif image_file.content_type == 'image/webp':
                image.save(output, format='WebP', quality=85)
            else:
                image.save(output, format=file_extension.upper())

            output.seek(0)
            processed_image = ContentFile(output.getvalue(), name=unique_filename)

        except Exception as e:
            # PIL 처리 실패 시 원본 파일 사용
            processed_image = image_file

        # S3에 업로드
        file_path = default_storage.save(s3_path, processed_image)
        file_url = default_storage.url(file_path)

        # 썸네일 생성 (선택적)
        thumbnail_url = None
        try:
            # 썸네일용 이미지 생성
            image.seek(0)  # PIL 이미지 다시 읽기
            thumbnail = image.copy()
            thumbnail.thumbnail((300, 300), Image.Resampling.LANCZOS)

            # 썸네일 저장
            thumbnail_output = io.BytesIO()
            if image_file.content_type == 'image/jpeg':
                thumbnail.save(thumbnail_output, format='JPEG', quality=80, optimize=True)
            elif image_file.content_type == 'image/png':
                thumbnail.save(thumbnail_output, format='PNG', optimize=True)
            elif image_file.content_type == 'image/webp':
                thumbnail.save(thumbnail_output, format='WebP', quality=80)
            else:
                thumbnail.save(thumbnail_output, format=file_extension.upper())

            thumbnail_output.seek(0)
            thumbnail_file = ContentFile(thumbnail_output.getvalue(), name=f"thumb_{unique_filename}")

            # 썸네일 S3 업로드
            thumbnail_path = f"chat_images/thumbnails/{unique_filename}"
            thumbnail_saved_path = default_storage.save(thumbnail_path, thumbnail_file)
            thumbnail_url = default_storage.url(thumbnail_saved_path)

        except Exception as e:
            # 썸네일 생성 실패 시 무시
            print(f"썸네일 생성 실패: {e}")

        return Response({
            'success': True,
            'image_url': file_url,
            'thumbnail_url': thumbnail_url,
            'filename': unique_filename,
            'size': processed_image.size,
            'content_type': image_file.content_type
        }, status=status.HTTP_201_CREATED)

    except Exception as e:
        return Response(
            {'error': f'이미지 업로드 실패: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


# 🔧 추가: 채팅방 알림 설정 API
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_chat_notification_settings(request):
    """사용자의 모든 채팅방 알림 설정 조회"""
    try:
        from .models import ChatNotificationSettings
        
        settings = ChatNotificationSettings.objects.filter(user=request.user)
        serializer = ChatNotificationSettingsSerializer(settings, many=True)
        
        return Response({
            'success': True,
            'settings': serializer.data
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response(
            {'error': f'알림 설정 조회 실패: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def toggle_chat_notification(request):
    """채팅방 알림 설정 토글"""
    try:
        from .models import ChatNotificationSettings, ChatRoom
        from .serializers import ChatNotificationSettingsSerializer
        
        chat_room_id = request.data.get('chat_room_id')
        if not chat_room_id:
            return Response(
                {'error': 'chat_room_id가 필요합니다'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 채팅방 조회 (UUID가 아닌 경우 클럽 ID로 조회)
        try:
            # UUID 형식인지 확인
            import uuid
            try:
                uuid.UUID(chat_room_id)
                chat_room = ChatRoom.objects.get(id=chat_room_id)
            except ValueError:
                # UUID가 아닌 경우 클럽 ID로 조회
                chat_room = ChatRoom.objects.get(club_id=int(chat_room_id), chat_room_type='CLUB')
        except ChatRoom.DoesNotExist:
            return Response(
                {'error': '채팅방을 찾을 수 없습니다'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # 기존 설정 조회 또는 생성
        setting, created = ChatNotificationSettings.objects.get_or_create(
            user=request.user,
            chat_room=chat_room,
            defaults={'is_enabled': True}
        )
        
        # 토글
        setting.is_enabled = not setting.is_enabled
        setting.save()
        
        serializer = ChatNotificationSettingsSerializer(setting)
        
        return Response({
            'success': True,
            'message': f'알림이 {"활성화" if setting.is_enabled else "비활성화"}되었습니다',
            'setting': serializer.data
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response(
            {'error': f'알림 설정 변경 실패: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_chat_room_info(request):
    """채팅방 정보 조회 (알림 설정 포함)"""
    try:
        from .models import ChatNotificationSettings
        from .serializers import ChatNotificationSettingsSerializer
        
        chat_room_id = request.GET.get('chat_room_id')
        if not chat_room_id:
            return Response(
                {'error': 'chat_room_id가 필요합니다'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 채팅방 조회 (UUID가 아닌 경우 클럽 ID로 조회)
        try:
            # UUID 형식인지 확인
            import uuid
            try:
                uuid.UUID(chat_room_id)
                chat_room = ChatRoom.objects.get(id=chat_room_id)
            except ValueError:
                # UUID가 아닌 경우 클럽 ID로 조회
                chat_room = ChatRoom.objects.get(club_id=int(chat_room_id), chat_room_type='CLUB')
        except ChatRoom.DoesNotExist:
            return Response(
                {'error': '채팅방을 찾을 수 없습니다'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # 사용자의 알림 설정 조회
        try:
            notification_setting = ChatNotificationSettings.objects.get(
                user=request.user,
                chat_room=chat_room
            )
            is_notification_enabled = notification_setting.is_enabled
        except ChatNotificationSettings.DoesNotExist:
            is_notification_enabled = True  # 기본값
        
        return Response({
            'success': True,
            'chat_room': {
                'id': str(chat_room.id),
                'name': chat_room.chat_room_name,
                'type': chat_room.chat_room_type,
                'is_notification_enabled': is_notification_enabled
            }
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response(
            {'error': f'채팅방 정보 조회 실패: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
