'''
MVP demo ver 0.0.1
2024.12.16
feedback/admins.py

역할: 유저로부터 받은 인앱 피드백을 관리자 페이지에서 볼 수 있음
'''
from django.contrib import admin

from feedbacks.models import Feedback


@admin.register(Feedback)
class FeedbackAdmin(admin.ModelAdmin):
    list_display = ('id', 'get_author_name', 'get_author_email', 'message', 'created_at')
    search_fields = ('author__id', 'author__email', 'author__name', 'message')
    list_filter = ('created_at',)

    def get_author_name(self, obj):
        return obj.author.name
    get_author_name.short_description = 'Author Name'

    def get_author_email(self, obj):
        return obj.author.email
    get_author_email.short_description = 'Author Email'

