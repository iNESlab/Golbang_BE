from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .serializers import FileUploadSerializer

class FileUploadAPIView(APIView):
    authentication_classes = []     # 인증 없이 접근
    permission_classes = [AllowAny]  # 모든 사용자 허용
    parser_classes = (MultiPartParser, FormParser)

    def post(self, request, format=None):
        serializer = FileUploadSerializer(data=request.data)
        if serializer.is_valid():
            file = serializer.validated_data['upload_file']
            content = file.read()
            # TODO: 파일 처리 로직
            return Response({"message": "파일 업로드 성공"}, status=status.HTTP_200_OK)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
