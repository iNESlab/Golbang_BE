'''
MVP demo ver 0.0.1
2024.06.19
accounts/admin.py
'''

from django.contrib import admin
from django.contrib.auth.models import Group
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.forms import AdminPasswordChangeForm  # TODO: 비밀번호 변경 후 다시 제거해야 함

from accounts.forms import UserChangeForm, UserCreationFirstStepForm
from accounts.models import User
'''
목록 보기: list_display
필터: list_filter
검색: search_fields
정렬: ordering
'''
class CustomUserAdmin(BaseUserAdmin):
    form = UserChangeForm
    add_form = UserCreationFirstStepForm
    # 관리자 화면에서 다른 유저 비밀번호 변경 폼을 사용하도록 설정
    change_password_form = AdminPasswordChangeForm # TODO: 비밀번호 변경 후 다시 제거해야 함

    list_display        = ('user_id', 'email', 'name', 'phone_number', 'handicap', 'date_of_birth', 'is_admin')
    list_filter         = ('is_admin',)
    fieldsets           = (
                            (None, {'fields': ('user_id', 'email', 'password')}),
                            ('Personal info', {'fields': ('name', 'phone_number', 'handicap', 'date_of_birth', 'address', 'student_id')}),
                            ('FCM token', {'fields': ('fcm_token',)}),
                            ('Permissions', {'fields': ('is_admin', 'is_active')}),
    )
    add_fieldsets       = (
                            (None, {
                                'classes': ('wide',),
                                'fields': ('user_id', 'email', 'password1', 'password2', 'name', 'phone_number', 'handicap', 'date_of_birth', 'address', 'student_id')}
                            ),
    )
    search_fields       = ('user_id', 'email', 'name')
    ordering            = ('email',)
    filter_horizontal   = ()

admin.site.register(User, CustomUserAdmin) # 생성한 커스텀 유저 모델(Custom User Model)과 관리자 폼(Form)을 사용하도록 등록
admin.site.unregister(Group) # 장고(djagno)에서 기본적으로 제공하는 Group은 사용하지 않도록 설