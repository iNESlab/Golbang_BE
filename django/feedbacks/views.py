from rest_framework import viewsets, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from .models import Feedback
from .serializers import FeedbackSerializer

class FeedbackViewSet(viewsets.ModelViewSet):

    serializer_class = FeedbackSerializer
    permission_classes = [IsAuthenticated]  # 사용자 인증 필요


    def create(self, request, *args, **kwargs):
        """
        피드백 생성 메서드
        요청 데이터: 메시지 (message)
        응답 데이터: 생성된 피드백 정보
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(author=self.request.user)
        response_data = {
            'status': status.HTTP_201_CREATED,
            'message': 'Successfully received feedback',
            'data': serializer.data
        }
        return Response(response_data, status=status.HTTP_201_CREATED)
