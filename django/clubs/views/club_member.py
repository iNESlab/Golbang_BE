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