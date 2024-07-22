'''
MVP demo ver 0.0.1
2024.06.19
accounts/form.py
'''

from django import forms
from django.contrib.auth.forms import ReadOnlyPasswordHashField
from .models import User

'''
사용자 생성 폼
'''
# step 1
# 첫 번째 단계 폼에서는 필수 항목인 user_id, password, email을 입력받는다.
class UserCreationFirstStepForm(forms.ModelForm):
    # widget을 이용하여 비밀번호가 화면에 표시되지 않도록 설정
    password1 = forms.CharField(label='Password', widget=forms.PasswordInput)
    password2 = forms.CharField(label='Password confirmation', widget=forms.PasswordInput)

    class Meta:
        # 폼에 포함할 모델과 필드
        model = User
        fields = ['user_id', 'email']

    # 비밀번호와 비밀번호 확인 필드의 값이 일치하는지 검증
    def clean_password2(self):
        password1 = self.cleaned_data.get("password1")
        password2 = self.cleaned_data.get("password2")
        if password1 and password2 and password1 != password2:
            # 일치 하지 않을 경우, ValidationError
            raise forms.ValidationError("Passwords don't match")
        return password2


    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password1"]) # 해시된 비밀번호로 저장
        if commit:
            user.save()
        return user

# step 2
# 두 번째 단계 폼에서는 추가 정보를 입력받는다.
class UserCreationSecondStepForm(forms.ModelForm):
    class Meta:
         # 폼에 포함할 모델과 필드
        model   = User
        fields  = ['name', 'phone_number', 'handicap', 'date_of_birth', 'address', 'student_id']

'''
사용자 수정 폼
'''
class UserChangeForm(forms.ModelForm):
    # password는 읽기 전용. (사용자 정보 수정시 비밀번호 변경 X)
    password = ReadOnlyPasswordHashField()

    class Meta:
        model   = User
        fields  = ['user_id', 'email', 'password', 'name', 'phone_number', 'handicap', 'date_of_birth', 'address', 'student_id',
                  'is_active', 'is_admin']

    def clean_password(self):
        # 비밀번호는 초기 상태 유지
        return self.initial["password"]