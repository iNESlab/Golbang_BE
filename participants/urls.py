from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ParticipantViewSet

# end point: api/v1/participant
router = DefaultRouter()
router.register(r'', ParticipantViewSet,'participants')

urlpatterns = [
    path('', include(router.urls)),
]