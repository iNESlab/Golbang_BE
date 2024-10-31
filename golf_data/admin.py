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

from utils.delete_s3_image import delete_s3_file

logger = logging.getLogger(__name__)

class ExcelFileUploadAdmin(admin.ModelAdmin):
    list_display = ('file', 'uploaded_at')

    def save_model(self, request, obj, form, change):
        # 기존 파일을 삭제하기 전에 S3 이미지 삭제 함수 호출
        existing_files = ExcelFileUpload.objects.all()
        for existing_file in existing_files:
            if existing_file.file and delete_s3_file(existing_file.file):
                print(f"=====기존 파일이 존재한다면 s3도 삭제!!!!")
                # S3에서 파일 삭제 성공 시 기존 데이터 삭제
                existing_file.delete()

        # 새로 업로드된 파일 저장
        super().save_model(request, obj, form, change)

        # S3 URL을 import_excel_data 함수에 전달하여 데이터 처리
        import_excel_data(obj.file.url)


admin.site.register(GolfClub)
admin.site.register(GolfCourse)
admin.site.register(Tee)
admin.site.register(ExcelFileUpload, ExcelFileUploadAdmin)
