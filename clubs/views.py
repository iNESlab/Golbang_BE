'''
MVP demo ver 0.0.6
2024.07.24
clubs/views.py

역할: Django Rest Framework(DRF)를 사용하여 모임 API 엔드포인트의 로직을 처리
기능:
- Authorization Type: Bearer Token
- ModelViewSet을 이용하여 모임의 CRUD 기능 구현
'''
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import Club, ClubMember
from .serializers import ClubSerializer, ClubCreateUpdateSerializer

class ClubViewSet(viewsets.ModelViewSet):
    queryset            = Club.objects.all() # 모든 Club 객체 가져오기
    serializer_class    = ClubSerializer
    permission_classes  = [IsAuthenticated]  # 인증된 사용자만 접근 가능

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return ClubCreateUpdateSerializer
        return ClubSerializer

    # 모임 생성 메서드
    def create(self, request, *args, **kwargs):
        '''
        POST 요청 시 모임(Club) 생성
        요청 데이터: 모임명, 설명, 이미지, 멤버, (모임) 관리자
        응답 데이터: 모임 정보 (club ID, 이름, 설명, 이미지, 멤버, 관리자, 생성일)
        '''
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        club            = serializer.save()

        # 일반 멤버와 관리자
        members = request.data.get('members', [])
        admins = request.data.get('admins', [])

        for member_id in members:
            ClubMember.objects.create(club=club, user_id=member_id, role='member')

        for admin_id in admins:
            ClubMember.objects.create(club=club, user_id=admin_id, role='admin')

        read_serializer = ClubSerializer(club)
        response_data   = {
            'code': status.HTTP_201_CREATED,
            'message': 'successfully Club created',
            'data': read_serializer.data
        }
        return Response(response_data, status=status.HTTP_201_CREATED)

    # 특정 모임 조회 메서드
    def retrieve(self, request, *args, **kwargs):
        """
        GET 요청 시 특정 모임(Club) 정보 반환
        요청 데이터: 모임 ID
        응답 데이터: 모임 정보 (ID, 이름, 설명, 이미지, 멤버, 관리자, 생성일)
        """
        instance    = self.get_object()
        serializer  = self.get_serializer(instance)
        response_data = {
            'status': status.HTTP_200_OK,
            'message': 'Successfully retrieved',
            'data': serializer.data
        }
        return Response(response_data, status=status.HTTP_200_OK)

    # 모임 정보 수정 메서드
    def update(self, request, *args, **kwargs):
        """
        PUT 요청 시 모임의 정보를 수정
        요청 데이터: 모임 정보 (이름, 설명, 이미지)
        응답 데이터: 수정된 모임 정보 (ID, 이름, 설명, 이미지, 수정일)
        """
        partial         = kwargs.pop('partial', False)
        instance        = self.get_object()
        serializer      = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        club            = serializer.save()
        read_serializer = ClubSerializer(club)
        response_data = {
            'status': status.HTTP_200_OK,
            'message': 'Successfully updated',
            'data': read_serializer.data
        }
        return Response(response_data, status=status.HTTP_200_OK)

    # 모임 삭제 메서드
    def destroy(self, request, *args, **kwargs):
        """
        DELETE 요청 시 모임 삭제
        요청 데이터: 모임 ID
        응답 데이터: 삭제 완료 메시지
        """
        instance = self.get_object()
        self.perform_destroy(instance)
        response_data = {
            'status': status.HTTP_204_NO_CONTENT,
            'message': 'Successfully Deleted the Club'
        }
        return Response(response_data, status=status.HTTP_204_NO_CONTENT)
