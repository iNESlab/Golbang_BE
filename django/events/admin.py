from django.contrib import admin
from .models import Event

# Event 모델을 관리자 페이지에서 볼 수 있도록 등록
admin.site.register(Event)
# Register your models here.
