'''
MVP demo ver 0.0.1
2024.06.27
accounts/social_login.py

역할: 사용자가 소셜 로그인 시, 사용자 정보를 처리하는 view
- 코드 가독성과 유지보수성을 높이기 위해 views.py로부터 파일을 분리
기능:
- 구글, 네이버, 카카오

'''
from rest_framework.views import APIView
from rest_framework import status
from accounts.models import User
from rest_framework.response import Response

import requests

from accounts.serializers import UserSerializer

class GoogleLogin(APIView):
    def post(self, request):
        token = request.data.get("token")
        if not token:
            return Response({"error": "Token is required"}, status=status.HTTP_400_BAD_REQUEST)

        google_response = requests.get(f'https://oauth2.googleapis.com/tokeninfo?id_token={token}')
        if google_response.status_code != 200:
            return Response({"error": "Invalid token"}, status=status.HTTP_400_BAD_REQUEST)

        google_data = google_response.json()
        email = google_data.get("email")

        if not email:
            return Response({"error": "Email not provided"}, status=status.HTTP_400_BAD_REQUEST)


        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            user = User.objects.create(
                email=email,
                userId=email.split('@')[0],
                login_type='social',
                provider='google',
            )
            user.save()

        serializer = UserSerializer(user)
        return Response(serializer.data, status=status.HTTP_200_OK)