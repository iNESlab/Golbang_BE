'''
MVP demo ver 0.0.3
2024.08.23
participa/stroke/data_class.py

기능: 참가자와 이벤트 데이터의 구조를 정의한 데이터 클래스
- 데이터 전송 시 필요한 정보를 캡슐화함
'''
from dataclasses import dataclass
from typing import Optional

from participants.models import Participant

@dataclass
class ParticipantUpdateData:
    rank: str
    handicap_rank: str
    sum_score: int
    handicap_score: int
    is_group_win: Optional[bool]
    is_group_win_handicap: Optional[bool]

    def __post_init__(self):
        if isinstance(self.is_group_win, str):
            self.is_group_win = bool(int(self.is_group_win))
        if isinstance(self.is_group_win_handicap, str):
            self.is_group_win_handicap = bool(int(self.is_group_win_handicap))
        for attr in ['sum_score', 'handicap_score']:
            value = getattr(self, attr)
            if isinstance(value, str):
                try:
                    setattr(self, attr, int(value)) # 음수도 int로 변환
                except (ValueError, TypeError):
                    pass


@dataclass
class EventData:
    group_win_team: str = "NONE"           # 그룹 승리 팀
    group_win_team_handicap: str = "NONE"  # 핸디캡 적용 그룹 승리 팀
    total_win_team: str = "NONE"           # 전체 승리 팀
    total_win_team_handicap: str = "NONE"  # 핸디캡 적용 전체 승리 팀

@dataclass
class RankResponseData:
    participant_id: int
    last_hole_number: int
    last_score: int
    rank: str
    handicap_rank: str
    sum_score: int
    handicap_score: int

    def __post_init__(self):
        for attr in ['participant_id', 'last_hole_number', 'last_score', 'sum_score', 'handicap_score']:
            value = getattr(self, attr)
            if isinstance(value, str):
                try:
                    setattr(self, attr, int(value)) # 음수도 int로 변환
                except (ValueError, TypeError):
                    pass

@dataclass
class ParticipantRedisData:
    participant_id: int
    event_id: int
    user_name: str
    user_handicap: int
    group_type: str
    team_type: str
    sum_score: int 
    handicap_score: int
    profile_image: Optional[str] = None
    is_group_win: bool = False
    is_group_win_handicap: bool = False
    rank: str = 'N/A'
    handicap_rank: str = 'N/A'

    def __post_init__(self):
        # 필드들이 bytes 타입인 경우 적절한 타입으로 변환
        for attr in ['participant_id', 'event_id', 'user_handicap', 'sum_score', 'handicap_score']:
            value = getattr(self, attr)
            if isinstance(value, str):
                try:
                    setattr(self, attr, int(value)) # 음수도 int로 변환
                except (ValueError, TypeError):
                    pass

        for attr in ['is_group_win', 'is_group_win_handicap']:
            value = getattr(self, attr)
            if isinstance(value, str) and value.isdigit():
                setattr(self, attr, bool(int(value)))

    @staticmethod
    def orm_to_participant_redis(participant: Participant) -> "ParticipantRedisData":
        return ParticipantRedisData(
            participant_id=participant.pk,
            profile_image=participant.club_member.user.profile_image.url if participant.club_member.user.profile_image else None,
            event_id=participant.event.pk,
            group_type=participant.group_type,
            team_type=participant.team_type,
            user_name=participant.club_member.user.name,
            user_handicap=participant.club_member.user.handicap,
            sum_score=participant.sum_score,
            handicap_score=participant.handicap_score,
            is_group_win=participant.is_group_win,
            is_group_win_handicap=participant.is_group_win_handicap,
            rank=participant.rank,
            handicap_rank=participant.handicap_rank
        )
    
    def to_redis_dict(self) -> dict[str, str]:
        return {
            "participant_id": str(self.participant_id),
            'profile_image': self.profile_image if self.profile_image else '',
            "event_id": str(self.event_id),
            "user_name": self.user_name,
            "user_handicap": str(self.user_handicap),
            "group_type": self.group_type,
            "team_type": self.team_type,
            "sum_score": str(self.sum_score),
            "handicap_score": str(self.handicap_score),
            "is_group_win": "1" if self.is_group_win else "0",
            "is_group_win_handicap": "1" if self.is_group_win_handicap else "0",
            "rank": self.rank,
            "handicap_rank": self.handicap_rank,
        }
