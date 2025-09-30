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

# TODO: UserSerializer 이동시키고 한 곳에서만 호출되도록
class UserSerializer(serializers.ModelSerializer):
    '''
    User 모델을 직렬화/역직렬화하는 클래스
    JSON 형식으로 변환하거나, JSON 데이터를 User 모델로 변환하는 데 사용됨
    '''
    class Meta:
        model   = User # 직렬화할 모델
        fields  = ('id', 'name', 'profile_image', 'email') # 직렬화할 모델의 필드 지정

class ClubMemberSerializer(serializers.ModelSerializer):
    '''
    ClubMember 모델을 직렬화하는 클래스
    클럽 내의 멤버의 멤버아이디, 이름, 역할에 대한 정보가 담김
    '''
    user= UserSerializer(read_only=True)
    member_id = serializers.PrimaryKeyRelatedField(source='id', read_only=True)
    is_current_user_admin = serializers.SerializerMethodField()  # 현재 사용자가 관리자인지 여부를 반환

    class Meta:
        model = ClubMember
        fields = ('user','member_id', 'role', 'status_type','is_current_user_admin')


    def get_is_current_user_admin(self, obj):
        '''
        현재 요청 사용자가 관리자인지 확인
        '''
        request = self.context.get('request')  # DRF에서 제공하는 요청 객체 가져오기
        if not request:
            return False

        current_user = request.user
        return obj.user == current_user and obj.role == 'admin'


class ClubSerializer(serializers.ModelSerializer):
    '''
    Club 모델을 직렬화하는 클래스
    클럽의 모든 정보를 포함한 JSON 응답을 생성
    '''
    members = ClubMemberSerializer(many=True, read_only=True, source='clubmember_set')  # 클럽 멤버 정보
    members_count = serializers.SerializerMethodField()  # 클럽 멤버 수
    is_admin = serializers.SerializerMethodField()  # 현재 요청 사용자가 클럽 관리자 여부 반환
    unread_count = serializers.SerializerMethodField()  # 🔧 추가: 읽지 않은 메시지 개수

    class Meta:
        model = Club
        # TODO: id -> club_id
        fields = ('id', 'name', 'description', 'image', 'members', 'members_count', 'created_at', 'is_admin', 'unread_count')

    def get_members_count(self, obj):
        '''
        클럽 멤버 수를 반환
        '''
        return obj.clubmember_set.filter(status_type='active').count()
    
    def get_is_admin(self, obj):
        '''
        현재 요청 사용자가 클럽 관리자 여부를 확인
        '''
        request = self.context.get('request')  # DRF에서 제공하는 요청 객체 가져오기
        if not request:
            return False

        current_user = request.user
        # ClubMember 중 현재 사용자가 admin인 경우 True 반환

        return obj.clubmember_set.filter(user=current_user, role='admin', status_type='active').exists()

    
    def get_unread_count(self, obj):
        '''
        클럽 채팅방의 읽지 않은 메시지 개수를 반환
        '''
        try:
            from chat.models import ChatRoom, ChatMessage
            
            request = self.context.get('request')
            if not request:
                return 0
                
            current_user = request.user
            
            # 클럽에 해당하는 채팅방 찾기
            try:
                chat_room = ChatRoom.objects.get(
                    chat_room_type='CLUB',
                    club_id=obj.id
                )
                
                # 읽지 않은 메시지 개수 계산 (자신이 보낸 메시지 제외)
                unread_count = ChatMessage.objects.filter(
                    chat_room=chat_room
                ).exclude(
                    sender=current_user  # 🔧 수정: 자신이 보낸 메시지 제외
                ).exclude(
                    read_statuses__user=current_user  # 읽음 상태가 있는 메시지 제외
                ).count()
                
                return unread_count
                
            except ChatRoom.DoesNotExist:
                # 채팅방이 없으면 0 반환
                return 0
                
        except Exception as e:
            # 오류 발생 시 0 반환
            return 0

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

# TODO: user의 모든 정보가 나오지 않도록 수정
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
    member_id = serializers.PrimaryKeyRelatedField(source='id', read_only=True)
    name = serializers.CharField(source='user.name')
    profile = serializers.ImageField(source='user.profile_image')
    total_events = serializers.SerializerMethodField()          # 총 이벤트 수
    participation_count = serializers.SerializerMethodField()   # 총 참석한 횟수
    participation_rate = serializers.SerializerMethodField()    # 참석율

    class Meta:
        model = ClubMember
        fields = ['member_id', 'name', 'profile', 'total_rank', 'total_handicap_rank', 'total_points', 'total_events',
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
        # 클럽 멤버가 참석한 총 이벤트 수를 반환 (ACCEPT와 PARTY 상태인 참가자만 포함)
        from participants.models import Participant
        return Participant.objects.filter(club_member=obj, status_type__in=['ACCEPT', 'PARTY']).count()

    def get_participation_rate(self, obj):
        # 참석률 계산
        total_events = self.get_total_events(obj)
        participation_count = self.get_participation_count(obj)
        return (participation_count / total_events * 100) if total_events > 0 else 0.0

# TODO: 제거
class ClubStatisticsSerializer(serializers.Serializer):
    from participants.serializers import EventStatisticsSerializer

    """
    클럽 통계 정보를 반환하는 메인 시리얼라이저
    """
    ranking = ClubRankingSerializer()
    events = EventStatisticsSerializer(many=True)

class ClubProfileSerializer(serializers.ModelSerializer):
    """
    간단한 클럽 프로필(id, 클럽명, 대표 이미지)
    """
    class Meta:
        model = Club  # 직렬화할 모델
        # TODO: id -> club_id
        fields = ('id', 'name', 'image')