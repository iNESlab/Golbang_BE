'''
MVP demo ver 0.0.1
2024.10.31
golf_data/views.py

기능:
전체 코스와 특정 골프장의 코스를 각각 조회
'''

# golf_data/views.py

from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import GolfClub
from .serializers import GolfClubSerializer
from rest_framework.decorators import permission_classes

@permission_classes([IsAuthenticated])
class GolfCourseViewSet(viewsets.ReadOnlyModelViewSet):
    """
    GolfClub 및 GolfCourse 정보 조회를 위한 ViewSet
    - 전체 골프장 코스 정보 조회 (list)
    - 특정 골프장 코스 정보 조회 (retrieve)
    """
    queryset = GolfClub.objects.all()
    serializer_class = GolfClubSerializer
    permission_classes = [IsAuthenticated]

    def get_permissions(self):
        """
        각 액션별 권한 설정:
        - 'retrieve', 'list' 액션은 인증된 사용자라면 접근 가능
        - 이외의 액션은 추가 권한을 설정할 수 있음
        """
        if self.action in ['retrieve', 'list']:
            self.permission_classes = [IsAuthenticated]  # 인증된 사용자 접근 가능
        return super().get_permissions()

    def list(self, request, *args, **kwargs):
        """
        전체 골프장 및 코스 정보 반환
        """
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def retrieve(self, request, *args, **kwargs):
        """
        특정 골프장 이름으로 조회하여 관련 코스 정보 반환
        """
        club_name = self.kwargs.get('club_name')
        golf_club = GolfClub.objects.filter(club_name=club_name).first()

        if golf_club:
            serializer = self.get_serializer(golf_club)
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response({"detail": "해당 골프장을 찾을 수 없습니다."}, status=status.HTTP_404_NOT_FOUND)
