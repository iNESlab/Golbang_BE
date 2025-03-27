import os

from rest_framework.permissions import AllowAny
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.renderers import TemplateHTMLRenderer, JSONRenderer

from django.http import FileResponse, Http404

from .serializers import FileUploadSerializer
from .prompting import process_excel_file
import tempfile


class FileUploadAPIView(APIView):
    authentication_classes = []     # 인증 없이 접근
    permission_classes = [AllowAny]  # 모든 사용자 허용
    parser_classes = (MultiPartParser, FormParser)
    renderer_classes = [JSONRenderer, TemplateHTMLRenderer]
    template_name = 'calculator/upload_form.html'

    def get(self, request, format=None):
        # GET 요청 시, HTML 폼을 렌더링
        context = {"message": None}
        return Response(context, template_name=self.template_name)

    def post(self, request, format=None):
        serializer = FileUploadSerializer(data=request.data)
        if serializer.is_valid():
            uploaded_file = serializer.validated_data['upload_file']
            try:
                output_path = process_excel_file(uploaded_file) # OpenAI API를 이용한 신페리오 핸디캡 계산 결과
                download_url = f"/calculator/download/?path={os.path.basename(output_path)}"
                print(f"download_url:{download_url}")
                return Response({
                    "message": "계산 완료!",
                    "download_url": download_url
                }, status=status.HTTP_200_OK)
            except Exception as e:
                return Response({
                    "error": str(e)
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        else:
            return Response({
                "error": serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)

class DownloadResultAPIView(APIView):
    """
    결과 엑셀 파일을 다운로드하는 뷰.
    다운로드 링크를 통해 파일 경로를 기반으로 파일을 반환한다.
    """
    authentication_classes = []  # 인증 없이 접근
    permission_classes = [AllowAny]  # 모든 사용자 허용

    def get(self, request, format=None):
        file_name = request.GET.get("path")
        if not file_name:
            raise Http404("파일 이름이 제공되지 않았습니다.")
        # 임시 저장 경로로부터 파일 경로를 복원합니다.
        file_path = os.path.join(tempfile.gettempdir(), file_name)
        if not os.path.exists(file_path):
            raise Http404("파일을 찾을 수 없습니다.")
        return FileResponse(open(file_path, 'rb'),
                            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                            as_attachment=True,
                            filename="newperio_handicap_result.xlsx")
