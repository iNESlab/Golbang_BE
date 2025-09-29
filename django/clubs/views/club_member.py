'''
MVP demo ver 0.0.8
2024.07.27
clubs/views/club_member.py

역할: Django Rest Framework(DRF)를 사용하여 모임 API 엔드포인트의 로직을 처리
- 모임 멤버: 모임 초대 수락/거절, 모임 나가기
'''
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, BasePermission

from django.http import Http404

from . import ClubViewSet
from ..models import Club, ClubMember
from utils.error_handlers import handle_404_not_found, handle_400_bad_request

# class IsMemberOfClub(BasePermission):
#     '''
#     사용자가 모임에 속한 멤버인지 확인하는 권한 클래스
#     '''
#     def has_permission(self, request, view):
#         # 요청한 사용자가 어떤 모임의 멤버인지 확인 (뷰 수준, 리스트 뷰, 생성 뷰에 사용)
#         # ex. 모임 목록 보기
#         return ClubMember.objects.filter(user=request.user).exists()
#
#     def has_object_permission(self, request, view, obj):
#         # 요청한 사용자가 특정 모임의 멤버인지 확인 (객체 수준, 특정 모임 객체 조회, 수정, 삭제 등에 사용)
#         # ex. 특정 모임 정보 보기
#         return ClubMember.objects.filter(club=obj, user=request.user).exists()

class ClubMemberViewSet(ClubViewSet):
    '''
    모임 멤버 관련 기능 제공 클래스
    '''
    # 초대 받은 멤버가 참여 수락/거절하는 메서드
    @action(detail=True, methods=['post'], url_path='join', url_name='join_club')
    def join_club(self, request, pk=None):
        try:
            club = self.get_object() # 모임 객체
        except Http404: # 모임이 존재하지 않는 경우, 404 반환
            return handle_404_not_found('Club', pk)

        user = request.user # JWT 토큰을 통해 인증된 사용자 정보를 가져옴
        status_choice = request.data.get('status')

        if status_choice not in ['accepted', 'declined']: # 유효하지 않은 데이터인 경우, 400 반환
            return handle_400_bad_request('Status must be \'accepted\' or \'declined\'')

        member = ClubMember.objects.filter(club=club, user=user).first()

        if status_choice == 'accepted':
            member.role = 'member'
            member.save()
            response_data = {
                'status': status.HTTP_200_OK,
                'message': 'Successfully joined the club',
                'data': {
                    'club_id': club.id,
                    'user_id': user.id,
                    'status': 'accepted'
                }
            }
        else:
            member.delete()
            response_data = {
                'status': status.HTTP_200_OK,
                'message': 'Successfully declined the club invitation',
                'data': {
                    'club_id': club.id,
                    'user_id': user.id,
                    'status': 'declined'
                }
            }

        return Response(response_data, status=status.HTTP_200_OK)

    # 모임 나가기 메서드
    @action(detail=True, methods=['delete'], url_path='leave', url_name='leave_club')
    def leave_club(self, request, pk=None):
        try:
            club = self.get_object() # 모임 객체
        except Http404: # 모임이 존재하지 않는 경우, 404 반환
            return handle_404_not_found('Club', pk)

        user = request.user
        member = ClubMember.objects.filter(club=club, user=user).first()

        return self.common_leave_club(member, user)
    
    @staticmethod
    def common_leave_club(member, user):
        

        if not member:  # 사용자가 해당 클럽의 멤버가 아닌 경우, 404 반환
            return handle_404_not_found('Club Member', user.id)

        member.delete() # 멤버 삭제

        return Response(status=status.HTTP_204_NO_CONTENT)

    # 🔧 추가: 초대 취소 API (관리자만 가능)
    @action(detail=True, methods=['post'], url_path='cancel-invitation', url_name='cancel_invitation')
    def cancel_invitation(self, request, pk=None):
        """
        관리자가 특정 사용자의 초대를 취소하는 API
        """
        try:
            club = self.get_object()
        except Http404:
            return handle_404_not_found('Club', pk)

        # 관리자 권한 확인
        if not ClubMember.objects.filter(club=club, user=request.user, role='admin').exists():
            return Response({
                'status': status.HTTP_403_FORBIDDEN,
                'message': '관리자만 초대를 취소할 수 있습니다.',
                'data': {}
            }, status=status.HTTP_403_FORBIDDEN)

        user_id = request.data.get('user_id')
        if not user_id:
            return handle_400_bad_request('user_id가 필요합니다.')

        try:
            member = ClubMember.objects.get(club=club, user_id=user_id, status_type='invited')
            member.delete()
            
            return Response({
                'status': status.HTTP_200_OK,
                'message': '초대가 취소되었습니다.',
                'data': {
                    'club_id': club.id,
                    'user_id': user_id,
                    'action': 'invitation_cancelled'
                }
            }, status=status.HTTP_200_OK)
            
        except ClubMember.DoesNotExist:
            return Response({
                'status': status.HTTP_404_NOT_FOUND,
                'message': '초대된 사용자를 찾을 수 없습니다.',
                'data': {}
            }, status=status.HTTP_404_NOT_FOUND)

    # 🔧 추가: 가입 신청 승인 API (관리자만 가능)
    @action(detail=True, methods=['post'], url_path='approve-application', url_name='approve_application')
    def approve_application(self, request, pk=None):
        """
        관리자가 가입 신청을 승인하는 API
        """
        try:
            club = self.get_object()
        except Http404:
            return handle_404_not_found('Club', pk)

        # 관리자 권한 확인
        if not ClubMember.objects.filter(club=club, user=request.user, role='admin').exists():
            return Response({
                'status': status.HTTP_403_FORBIDDEN,
                'message': '관리자만 가입 신청을 승인할 수 있습니다.',
                'data': {}
            }, status=status.HTTP_403_FORBIDDEN)

        user_id = request.data.get('user_id')
        if not user_id:
            return handle_400_bad_request('user_id가 필요합니다.')

        try:
            member = ClubMember.objects.get(club=club, user_id=user_id, status_type='applied')
            member.status_type = 'active'
            member.save()
            
            # 🔧 추가: 가입 승인 알림 전송
            try:
                from utils.push_fcm_notification import send_club_application_result_notification
                send_club_application_result_notification(club, member.user, True)
            except Exception as e:
                logger.error(f"가입 승인 알림 전송 실패: {e}")
            
            return Response({
                'status': status.HTTP_200_OK,
                'message': '가입 신청이 승인되었습니다.',
                'data': {
                    'club_id': club.id,
                    'user_id': user_id,
                    'status_type': 'active',
                    'action': 'application_approved'
                }
            }, status=status.HTTP_200_OK)
            
        except ClubMember.DoesNotExist:
            return Response({
                'status': status.HTTP_404_NOT_FOUND,
                'message': '가입 신청자를 찾을 수 없습니다.',
                'data': {}
            }, status=status.HTTP_404_NOT_FOUND)

    # 🔧 추가: 가입 신청 거절 API (관리자만 가능)
    @action(detail=True, methods=['post'], url_path='reject-application', url_name='reject_application')
    def reject_application(self, request, pk=None):
        """
        관리자가 가입 신청을 거절하는 API
        """
        try:
            club = self.get_object()
        except Http404:
            return handle_404_not_found('Club', pk)

        # 관리자 권한 확인
        if not ClubMember.objects.filter(club=club, user=request.user, role='admin').exists():
            return Response({
                'status': status.HTTP_403_FORBIDDEN,
                'message': '관리자만 가입 신청을 거절할 수 있습니다.',
                'data': {}
            }, status=status.HTTP_403_FORBIDDEN)

        user_id = request.data.get('user_id')
        if not user_id:
            return handle_400_bad_request('user_id가 필요합니다.')

        try:
            member = ClubMember.objects.get(club=club, user_id=user_id, status_type='applied')
            member.status_type = 'rejected'
            member.save()
            
            # 🔧 추가: 가입 거절 알림 전송
            try:
                from utils.push_fcm_notification import send_club_application_result_notification
                send_club_application_result_notification(club, member.user, False)
            except Exception as e:
                logger.error(f"가입 거절 알림 전송 실패: {e}")
            
            return Response({
                'status': status.HTTP_200_OK,
                'message': '가입 신청이 거절되었습니다.',
                'data': {
                    'club_id': club.id,
                    'user_id': user_id,
                    'status_type': 'rejected',
                    'action': 'application_rejected'
                }
            }, status=status.HTTP_200_OK)
            
        except ClubMember.DoesNotExist:
            return Response({
                'status': status.HTTP_404_NOT_FOUND,
                'message': '가입 신청자를 찾을 수 없습니다.',
                'data': {}
            }, status=status.HTTP_404_NOT_FOUND)

    # 🔧 추가: 멤버 상태 변경 API (관리자만 가능)
    @action(detail=True, methods=['post'], url_path='change-status', url_name='change_member_status')
    def change_member_status(self, request, pk=None):
        """
        관리자가 멤버의 상태를 변경하는 API
        """
        try:
            club = self.get_object()
        except Http404:
            return handle_404_not_found('Club', pk)

        # 관리자 권한 확인
        if not ClubMember.objects.filter(club=club, user=request.user, role='admin').exists():
            return Response({
                'status': status.HTTP_403_FORBIDDEN,
                'message': '관리자만 멤버 상태를 변경할 수 있습니다.',
                'data': {}
            }, status=status.HTTP_403_FORBIDDEN)

        user_id = request.data.get('user_id')
        new_status = request.data.get('status_type')
        
        if not user_id or not new_status:
            return handle_400_bad_request('user_id와 status_type이 필요합니다.')

        # 유효한 상태 타입 확인
        valid_statuses = ['invited', 'applied', 'active', 'rejected', 'banned']
        if new_status not in valid_statuses:
            return handle_400_bad_request(f'유효하지 않은 상태입니다. 가능한 값: {", ".join(valid_statuses)}')

        try:
            member = ClubMember.objects.get(club=club, user_id=user_id)
            old_status = member.status_type
            member.status_type = new_status
            member.save()
            
            return Response({
                'status': status.HTTP_200_OK,
                'message': f'멤버 상태가 {old_status}에서 {new_status}로 변경되었습니다.',
                'data': {
                    'club_id': club.id,
                    'user_id': user_id,
                    'old_status': old_status,
                    'new_status': new_status,
                    'action': 'status_changed'
                }
            }, status=status.HTTP_200_OK)
            
        except ClubMember.DoesNotExist:
            return Response({
                'status': status.HTTP_404_NOT_FOUND,
                'message': '멤버를 찾을 수 없습니다.',
                'data': {}
            }, status=status.HTTP_404_NOT_FOUND)