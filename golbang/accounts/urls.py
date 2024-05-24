# accounts/urls.py

from django.urls import path, include

urlpatterns = [
    path('', include('dj_rest_auth.urls')), # 로그인
    path('registration/', include('dj_rest_auth.registration.urls')), # 회원가입
]

'''
dj_rest_auth을 사용하는 경우, 아래 url을 모두 사용할 수 있다.
golbang/accounts/v1/ password/reset/ [name='rest_password_reset']
golbang/accounts/v1/ password/reset/confirm/ [name='rest_password_reset_confirm']
golbang/accounts/v1/ login/ [name='rest_login']
golbang/accounts/v1/ logout/ [name='rest_logout']
golbang/accounts/v1/ user/ [name='rest_user_details']
golbang/accounts/v1/ password/change/ [name='rest_password_change']
golbang/accounts/v1/ registration/
'''