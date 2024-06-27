'''
MVP demo ver 0.0.1
2024.06.27
accounts/social_login.py

역할: 사용자가 소셜 로그인 시, 사용자 정보를 처리하는 view
- 코드 가독성과 유지보수성을 높이기 위해 views.py로부터 파일을 분리
기능:
- 구글
'''
from django.urls import reverse
import requests
from django.conf import settings
from django.shortcuts import redirect, render
from django.contrib.auth import get_user_model

User = get_user_model()

def google_login(request):
    """
    구글 로그인 URL로 리디렉션
    """
    google_client_id = settings.SOCIAL_AUTH_GOOGLE_OAUTH2_KEY
    redirect_uri = request.build_absolute_uri(reverse('google_callback'))
    google_auth_url = (
        f"https://accounts.google.com/o/oauth2/auth?response_type=code"
        f"&client_id={google_client_id}&redirect_uri={redirect_uri}"
        f"&scope=openid%20email%20profile"
    )
    return redirect(google_auth_url)

def google_callback(request):
    """
    구글 OAuth2 콜백 처리
    """
    code = request.GET.get('code')
    if not code:
        return redirect('google_login')

    google_client_id = settings.SOCIAL_AUTH_GOOGLE_OAUTH2_KEY
    google_client_secret = settings.SOCIAL_AUTH_GOOGLE_OAUTH2_SECRET
    redirect_uri = request.build_absolute_uri(reverse('google_callback'))
    token_url = "https://oauth2.googleapis.com/token"
    token_data = {
        "code": code,
        "client_id": google_client_id,
        "client_secret": google_client_secret,
        "redirect_uri": redirect_uri,
        "grant_type": "authorization_code",
    }
    token_response = requests.post(token_url, data=token_data)
    token_json = token_response.json()
    access_token = token_json.get('access_token')
    id_token = token_json.get('id_token')

    user_info_url = "https://www.googleapis.com/oauth2/v3/userinfo"
    user_info_response = requests.get(user_info_url, headers={"Authorization": f"Bearer {access_token}"})
    user_info = user_info_response.json()

    email = user_info.get("email")
    if not email:
        return redirect('google_login')

    try:
        user = User.objects.get(email=email)
    except User.DoesNotExist:
        password = User.objects.make_random_password()
        user = User.objects.create(
            email=email,
            userId=email.split('@')[0],
            login_type='social',
            provider='google',
            password=password
        )
        user.save()
        
    # 세션에 사용자 이메일 저장
    request.session['user_email'] = email

    # 로그인 후 리디렉션할 뷰로 변경
    return redirect('login_success')

def login_success(request):
    """
    로그인 성공 페이지 렌더링
    """
    user_email = request.session.get('user_email')
    if not user_email:
        return redirect('google_login_test')

    user = User.objects.get(email=user_email)
    print("로그인 성공: ", user)
    return render(request, 'login_success.html', {'user': user})
