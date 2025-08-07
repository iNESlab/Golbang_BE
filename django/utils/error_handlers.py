'''
MVP demo ver 0.0.1
2024.07.28
utils/error_handlers.py

기능: 커스텀 예외 핸들러 및 공통 에러 처리 함수들
'''
from rest_framework.views import exception_handler
from rest_framework.exceptions import PermissionDenied
from rest_framework import status
from rest_framework.response import Response

def custom_exception_handler(exc, context):
    """
    커스텀 예외 핸들러
    """
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

"""
공통 에러 처리 함수
"""
def handle_club_400_invalid_serializer(serializer):
    errors = {
        "name": "Name field is required and must be a non-empty string" if "name" in serializer.errors else None,
        "description": "Description field must be a string" if "description" in serializer.errors else None,
        "image": "Image URL must be a valid URL" if "image" in serializer.errors else None,
        "members": "Members field must be a list of valid user IDs" if "members" in serializer.errors else None,
        "admins": "Admins field must be a list of valid user IDs, and at least one admin must be specified" if "admins" in serializer.errors else None,
    }
    return Response({
        "status": 400,
        "message": "Invalid request payload",
        "errors": {k: v for k, v in errors.items() if v is not None}
    }, status=status.HTTP_400_BAD_REQUEST)


def handle_404_not_found(model_name, pk):
    return Response({
        'status': 404,
        'message': f'{model_name} {pk} is not found'
    }, status=status.HTTP_404_NOT_FOUND)


def handle_400_bad_request(message):
    return Response({
        'status': 400,
        'message': message
    }, status=status.HTTP_400_BAD_REQUEST)

def handle_401_unauthorized(message):
    return Response({
        'status': 401,
        'message': message
    }, status=status.HTTP_401_UNAUTHORIZED)

def handle_403_FORBIDDEN(message):
    return Response({
        'status': 403,
        'message': message
    }, status=status.HTTP_403_FORBIDDEN)
