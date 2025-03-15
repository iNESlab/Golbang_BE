"""
MVP demo ver 0.1.0
2025.03.15
golf_data/views.py

기능:
- 전체 골프장 목록 조회 (list)
- 특정 골프장 조회 (retrieve)
"""
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404

from utils.error_handlers import handle_404_not_found
from .models import GolfClub
from .serializers import GolfClubDetailSerializer, GolfClubListSerializer


class GolfCourseViewSet(viewsets.ReadOnlyModelViewSet):
    """
    GolfClub 및 GolfCourse 정보 조회를 위한 ViewSet
    - 전체 골프장 코스 정보 조회 (list)
    - 특정 골프장 코스 정보 조회 (query param 방식)
    """
    queryset = GolfClub.objects.all()
    permission_classes = [IsAuthenticated]

    def list(self, request, *args, **kwargs):
        """
        1. 전체 골프장 목록 조회 (GET)
        2. 특정 골프장 ID (`golfclub_id`)가 있으면 해당 골프장 정보만 반환
        """
        golfclub_id = request.query_params.get("golfclub_id")  # Query Parameter에서 `golfclub_id` 가져오기

        if golfclub_id:
            golf_club = get_object_or_404(GolfClub, id=golfclub_id)  # 404 처리 포함
            serializer = GolfClubDetailSerializer(golf_club)
            response_data = {
                'status': status.HTTP_200_OK,
                'message': f'Successfully retrieved golf club with id {golfclub_id}',
                'data': serializer.data
            }
            return Response(response_data, status=status.HTTP_200_OK)

        # `golfclub_id`가 없을 경우 전체 목록 반환
        # TODO: 예외처리 필요함
        queryset = self.get_queryset()
        serializer = GolfClubListSerializer(queryset, many=True)
        response_data = {
            'status': status.HTTP_200_OK,
            'message': 'Successfully retrieved golf club list',
            'data': serializer.data
        }
        return Response(response_data, status=status.HTTP_200_OK)
