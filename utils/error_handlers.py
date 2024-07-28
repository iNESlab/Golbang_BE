from rest_framework import status
from rest_framework.response import Response

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
