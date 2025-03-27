from django.urls import path
from .views import FileUploadAPIView, DownloadResultAPIView

app_name = 'calculator'

urlpatterns = [
    path('upload/', FileUploadAPIView.as_view(), name='file-upload'),
    path('download/', DownloadResultAPIView.as_view(), name='file-download'),
]