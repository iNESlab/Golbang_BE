'''
MVP demo ver 0.0.2
2024.10.31
golf_data/admin.py

역할: admin 페이지에서 엑셀 파일을 업로드하면 기능이 동작됨
'''
# golf_data/admin.py
import logging

from django.contrib import admin
from .models import GolfClub, GolfCourse, Tee, ExcelFileUpload
from .data_import import import_excel_data

from utils.delete_s3_image import delete_s3_image

logger = logging.getLogger(__name__)

class ExcelFileUploadAdmin(admin.ModelAdmin):
    list_display = ('file', 'uploaded_at')

    def save_model(self, request, obj, form, change):
        # 새로운 파일 업로드 전에 기존 파일 삭제
        ExcelFileUpload.objects.all().delete()

        # 새로 업로드된 파일 저장
        super().save_model(request, obj, form, change)

        # S3 URL을 import_excel_data 함수에 전달하여 데이터 처리
        import_excel_data(obj.file.url)

    def delete_model(self, request, obj):
        """파일 삭제 시 관련 데이터도 함께 삭제하도록 구현"""
        # 파일이 존재하는지 확인
        if obj.file:
            if delete_s3_image(obj.file):
                obj.file.delete(save=False)  # S3에 저장된 파일 삭제
                super().delete_model(request, obj)
            else:
                logger.error(f"S3에서 파일 삭제 실패: {obj.file.name}")
        else:
            logger.warning("삭제 요청 시 파일이 존재하지 않습니다.")
            super().delete_model(request, obj)

admin.site.register(GolfClub)
admin.site.register(GolfCourse)
admin.site.register(Tee)
admin.site.register(ExcelFileUpload, ExcelFileUploadAdmin)
