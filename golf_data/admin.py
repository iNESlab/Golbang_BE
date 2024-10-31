'''
MVP demo ver 0.0.1
2024.10.31
golf_data/admin.py

역할: admin 페이지에서 엑셀 파일을 업로드하면 기능이 동작됨
'''
# golf_data/admin.py
from django.contrib import admin
from .models import GolfClub, GolfCourse, Tee, ExcelFileUpload
from .data_import import import_excel_data

class ExcelFileUploadAdmin(admin.ModelAdmin):
    list_display = ('file', 'uploaded_at')

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        # S3 URL을 import_excel_data 함수에 전달
        import_excel_data(obj.file.url)

admin.site.register(GolfClub)
admin.site.register(GolfCourse)
admin.site.register(Tee)
admin.site.register(ExcelFileUpload, ExcelFileUploadAdmin)
