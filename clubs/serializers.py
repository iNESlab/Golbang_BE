'''
MVP demo ver 0.0.4
2024.07.25
clubs/serializers.py

역할:
Django REST Framework에서 데이터의 직렬화(Serialization)와 역직렬화(Deserialization)를 처리하는 역할로
모임(Club) 모델에 대한 직렬화(Serialization) 로직을 정의
기능:
- 모임 및 사용자 데이터를 JSON 형식으로 변환
- 모임 생성 및 업데이트 시 사용되는 데이터 검증
'''

from rest_framework import serializers

from .models import Club, ClubMember
from django.contrib.auth import get_user_model

from .utils import calculate_event_points

User = get_user_model()

class UserSerializer(serializers.ModelSerializer):
    '''
    User 모델을 직렬화/역직렬화하는 클래스
    JSON 형식으로 변환하거나, JSON 데이터를 User 모델로 변환하는 데 사용됨
    '''
    class Meta:
        model   = User # 직렬화할 모델
        fields  = ('id', 'name', 'email') # 직렬화할 모델의 필드 지정

class ClubMemberSerializer(serializers.ModelSerializer):
    '''
    ClubMember 모델을 직렬화하는 클래스
    클럽 내의 멤버의 역할에 대한 정보가 담김
    '''
    user = UserSerializer()

    class Meta:
        model = ClubMember
        fields = ('user', 'role')

class ClubSerializer(serializers.ModelSerializer):
    '''
    Club 모델을 직렬화하는 클래스
    클럽의 모든 정보를 포함한 JSON 응답을 생성
    '''
    members = ClubMemberSerializer(many=True, read_only=True, source='clubmember_set')

    class Meta:
        model   = Club # 직렬화할 모델
        fields  = ('id', 'name', 'description', 'image', 'members', 'created_at')

class ClubCreateUpdateSerializer(serializers.ModelSerializer):
    '''
    모임을 생성하거나 업데이트할 때 사용되는 데이터의 직렬화/역직렬화를 처리하는 클래스
    모임의 생성 및 업데이트를 위한 유효성 검사를 수행하고, 유효한 데이터를 모델 인스턴스로 변환
    모임 생성 시 "name"은 필수이고, "description"과 "image"는 필수가 아님
    '''
    name = serializers.CharField(required=True)
    description = serializers.CharField(required=False, allow_blank=True)
    image = serializers.ImageField(required=False, allow_null=True)

    class Meta:
        model   = Club
        fields  = ('name', 'description', 'image')

class ClubMemberAddSerializer(serializers.ModelSerializer):
    '''
    클럽에 멤버를 추가할 때 사용되는 데이터의 직렬화/역직렬화를 처리하는 클래스
    '''
    class Meta:
        model = ClubMember
        fields = ('user', 'role')

class ClubAdminAddSerializer(serializers.ModelSerializer):
    '''
    클럽에 관리자를 추가할 때 사용되는 데이터의 직렬화/역직렬화를 처리하는 클래스
    '''
    class Meta:
        model = ClubMember
        fields = ('user', 'role')

class ClubRankingSerializer(serializers.ModelSerializer):
    """
    클럽 멤버의 랭킹 정보를 직렬화하는 시리얼라이저
    """
    club_id = serializers.PrimaryKeyRelatedField(source='id', read_only=True)
    total_events = serializers.SerializerMethodField()          # 총 이벤트 수
    participation_count = serializers.SerializerMethodField()   # 총 참석한 횟수
    participation_rate = serializers.SerializerMethodField()    # 참석율

    class Meta:
        model = ClubMember
        fields = ['club_id', 'total_rank', 'total_handicap_rank', 'total_points', 'total_events',
                  'participation_count', 'participation_rate']

    def get_total_events(self, obj):
        from events.models import Event

        """
        클럽에 관련된 총 이벤트 수를 반환
        """
        club = obj.club
        total_events = Event.objects.filter(club=club).count()
        return total_events

    def get_participation_count(self, obj):
        # 참가자가 참석한 총 이벤트 수
        return obj.participant_set.count()

    def get_participation_rate(self, obj):
        # 참석률 계산
        total_events = self.get_total_events(obj)
        participation_count = self.get_participation_count(obj)
        return (participation_count / total_events * 100) if total_events > 0 else 0.0


class ClubStatisticsSerializer(serializers.Serializer):
    from participants.serializers import EventStatisticsSerializer

    """
    클럽 통계 정보를 반환하는 메인 시리얼라이저
    """
    ranking = ClubRankingSerializer()
    events = EventStatisticsSerializer(many=True)
