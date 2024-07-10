'''
MVP demo ver 0.0.3
2024.07.09
clubs/views.py

역할: Django Rest Framework(DRF)를 사용하여 모임 API 엔드포인트의 로직을 처리
기능:
- 모임 생성, 조회, 수정, 삭제
'''

from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import Club
from .serializers import ClubSerializer, ClubCreateUpdateSerializer

class ClubViewSet(viewsets.ModelViewSet):
    queryset = Club.objects.all()
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return ClubCreateUpdateSerializer
        return ClubSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        club = serializer.save()
        read_serializer = ClubSerializer(club)
        return Response(read_serializer.data, status=status.HTTP_201_CREATED)
