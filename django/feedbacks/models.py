'''
MVP demo ver 0.0.1
2024.12.16
feedback/models.py

역할: 피드백을 저장할 수 있는 테이블
'''
from django.db import models
from django.contrib.auth import get_user_model


User = get_user_model()

class Feedback(models.Model):
    id = models.AutoField(primary_key=True)
    author = models.ForeignKey(User, on_delete=models.CASCADE)
    message = models.TextField("피드백 내용")
    created_at = models.DateTimeField("생성일", auto_now_add=True)

    def __str__(self):
        return f"{self.author.email}: {self.message[:50]}"
