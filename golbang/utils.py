'''
MVP demo ver 0.0.1
2024.07.27
golbang/utils.py

기능: 커스텀 예외 핸들러
(이외는 DRF의 기본 예외처리도 사용 가능)
'''
from rest_framework.views import exception_handler
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from rest_framework import status


def custom_exception_handler(exc, context):
    # 기본 예외 핸들러를 호출하여 기본 응답을 가져옴
    response = exception_handler(exc, context)

    # PermissionDenied 예외를 커스터마이징하여 처리
    if isinstance(exc, PermissionDenied):
        return Response({
            'status': status.HTTP_403_FORBIDDEN,
            'message': '이 작업을 수행할 권한(permission)이 없습니다.'
        }, status=status.HTTP_403_FORBIDDEN)

    # 기본 예외 핸들러에서 처리하지 않은 다른 예외는 그대로 반환
    return response