'''
MVP demo ver 0.0.4
2024.07.22
clubs/views.py

역할: Django Rest Framework(DRF)를 사용하여 모임 API 엔드포인트의 로직을 처리
기능:
- ModelViewSet을 이용하여 모임의 CRUD 기능 구현
'''
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from .models import Club
from .serializers import ClubSerializer, ClubCreateUpdateSerializer

class ClubViewSet(viewsets.ModelViewSet):
    queryset = Club.objects.all()           # 모든 Club 객체 가져오기
    permission_classes = [IsAuthenticated]  # 인증된 사용자만 접근 가능

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return ClubCreateUpdateSerializer
        return ClubSerializer

    # 모임 생성 메서드
    def create(self, request, *args, **kwargs):
        '''
        POST 요청 시 처리되는 함수
        '''
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        club = serializer.save()
        read_serializer = ClubSerializer(club)
        response_data = {
            'code': status.HTTP_201_CREATED,
            'message': 'Club created successfully',
            'data': read_serializer.data
        }
        return Response(response_data, status=status.HTTP_201_CREATED)
