'''
MVP demo ver 0.0.1
2024.07.23
clubs/admin.py
'''
from django.contrib import admin
from clubs.models import Club, ClubMember

'''
목록 보기: list_display
필터: list_filter
검색: search_fields
정렬: ordering
'''

admin.site.register(ClubMember)

@admin.register(Club)
class ClubAdmin(admin.ModelAdmin):
    list_display    = ('name', 'created_at')
    list_filter     = ('created_at',)
    search_fields   = ('name', 'members')
    ordering        = ('name', 'created_at',)
