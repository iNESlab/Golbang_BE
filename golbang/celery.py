# golbang/celery.py

from __future__ import absolute_import, unicode_literals
import os
from celery import Celery

from golbang import settings

# DJANGO_SETTINGS_MODULE의 환경 변수를 설정해준다.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'golbang.settings')

# Celery 애플리케이션을 생성한다.
app = Celery('golbang')

# Django 설정 파일에서 Celery 관련 설정을 불러온다.
app.config_from_object('django.conf:settings', namespace='CELERY')
# namespace를 설정해준 것은 celery 구성 옵션들이 모두 앞에 CELERY_가 붙게 되는 것을 의미

# 다음을 추가해주면 celery가 자동적으로 tasks를 찾는데, 우리가 설치되어 있는 앱에서 찾아준다.
app.autodiscover_tasks(lambda: settings.INSTALLED_APPS)

@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')
