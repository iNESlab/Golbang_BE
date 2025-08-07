# golbang/__init__.py

from __future__ import absolute_import, unicode_literals

# Celery 앱을 임포트하여 Django가 Celery를 로드하도록 합니다.
from .celery import app as celery_app

__all__ = ['celery_app']