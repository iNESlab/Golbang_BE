'''
MVP demo ver 0.0.8
2024.07.27
clubs/views/

역할: Django Rest Framework(DRF)를 사용하여 모임 API 엔드포인트의 로직을 처리
'''

from .club_common import ClubViewSet        # 모임 공통 기능
from .club_admin import ClubAdminViewSet    # 모임 내 관리자 기능
from .club_member import ClubMemberViewSet  # 모임 내 멤버 기능