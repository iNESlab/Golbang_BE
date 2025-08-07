'''
MVP demo ver 0.0.1
2024.06.19
accounts/serializers.py

Django Rest Framework를 사용하여 데이터를 JSON으로 직렬화하거나 JSON 데이터를 파이썬 객체로 역직렬화하는 역할을 한다.
API 응답으로 JSON 데이터를 제공하거나, API 요청으로 받은 JSON 데이터를 처리하는 데 사용된다.
'''
from django.contrib.auth import get_user_model # Django 설정에서 AUTH_USER_MODEL로 지정된 모델을 반환
from rest_framework import serializers # 직렬화 도구

# 사용자 모델의 직렬화 및 역직렬화를 처리
class UserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True) # passwords는 읽기 전용으로, 응답 (JSON 객체)에 포함되지 않음

    class Meta:
        # 직렬화할 모델과 포함할 필드들을 정의
        model   = get_user_model()
        fields  = ('user_id', 'email', 'password', 'name')


# 사용자 정보(자기 자신) 조회 시리얼라이저
class UserInfoSerializer(serializers.ModelSerializer):
    class Meta:
        model = get_user_model()
        fields = (
            # TODO: id->account_id
            'id', 'user_id', 'profile_image', 'name', 'email', 'phone_number',
            'handicap', 'address', 'date_of_birth', 'student_id'
        )
# 다른 사용자 정보 조회 시리얼라이저
class OtherUserInfoSerializer(serializers.ModelSerializer):
    class Meta:
        model = get_user_model()
        fields = (
            # TODO: id->account_id
            'id', 'user_id', 'profile_image', 'name'
        )