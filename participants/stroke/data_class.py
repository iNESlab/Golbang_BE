'''
MVP demo ver 0.0.3
2024.08.23
participa/stroke/data_class.py

기능: 참가자와 이벤트 데이터의 구조를 정의한 데이터 클래스
- 데이터 전송 시 필요한 정보를 캡슐화함
'''
from dataclasses import dataclass
from typing import Optional


@dataclass
class ParticipantUpdateData:
    participant_id: int
    rank: str
    handicap_rank: str
    sum_score: int
    handicap_score: int
    is_group_win: Optional[bool]
    is_group_win_handicap: Optional[bool]

    def __post_init__(self):
        # rank와 handicap_rank가 bytes 타입인 경우 문자열로 디코딩
        if isinstance(self.rank, bytes):
            self.rank = self.rank.decode('utf-8')
        if isinstance(self.handicap_rank, bytes):
            self.handicap_rank = self.handicap_rank.decode('utf-8')
        # is_group_win과 is_group_win_handicap이 bytes 타입인 경우 boolean으로 변환
        if isinstance(self.is_group_win, bytes):
            self.is_group_win = bool(int(self.is_group_win))
        if isinstance(self.is_group_win_handicap, bytes):
            self.is_group_win_handicap = bool(int(self.is_group_win_handicap))


@dataclass
class EventData:
    group_win_team: Optional[str]           # 그룹 승리 팀
    group_win_team_handicap: Optional[str]  # 핸디캡 적용 그룹 승리 팀
    total_win_team: Optional[str]           # 전체 승리 팀
    total_win_team_handicap: Optional[str]  # 핸디캡 적용 전체 승리 팀

    def __post_init__(self):
        # 필드들이 bytes 타입인 경우 문자열로 디코딩
        if isinstance(self.group_win_team, bytes):
            self.group_win_team = self.group_win_team.decode('utf-8')
        if isinstance(self.group_win_team_handicap, bytes):
            self.group_win_team_handicap = self.group_win_team_handicap.decode('utf-8')
        if isinstance(self.total_win_team, bytes):
            self.total_win_team = self.total_win_team.decode('utf-8')
        if isinstance(self.total_win_team_handicap, bytes):
            self.total_win_team_handicap = self.total_win_team_handicap.decode('utf-8')

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
        if isinstance(self.participant_id, bytes):
            self.participant_id = int(self.participant_id)
        if isinstance(self.last_hole_number, bytes):
            self.last_hole_number = int(self.last_hole_number)
        if isinstance(self.last_score, bytes):
            self.last_score = int(self.last_score)
        if isinstance(self.rank, bytes):
            self.rank = self.rank.decode('utf-8')
        if isinstance(self.handicap_rank, bytes):
            self.handicap_rank = self.handicap_rank.decode('utf-8')
        if isinstance(self.sum_score, bytes):
            self.sum_score = int(self.sum_score)
        if isinstance(self.handicap_score, bytes):
            self.handicap_score = int(self.handicap_score)

@dataclass
class ParticipantResponseData:
    participant_id: int
    user_name: chr
    group_type: chr
    team_type: chr
    is_group_win: Optional[bool]
    is_group_win_handicap: Optional[bool]
    hole_number: int = 0
    score: int = 0
    sum_score: int = 0
    handicap_score: int = 0
    rank: str = 'N/A'
    handicap_rank: str = 'N/A'

    def __post_init__(self):
        # 필드들이 bytes 타입인 경우 적절한 타입으로 변환
        if isinstance(self.participant_id, bytes):
            self.participant_id = int(self.participant_id)
        if isinstance(self.user_name, bytes):
            self.user_name = self.user_name.decode('utf-8')
        if isinstance(self.group_type, bytes):
            self.group_type = self.group_type.decode('utf-8')
        if isinstance(self.team_type, bytes):
            self.team_type = self.team_type.decode('utf-8')
        if isinstance(self.rank, bytes):
            self.rank = self.rank.decode('utf-8')
        if isinstance(self.handicap_rank, bytes):
            self.handicap_rank = self.handicap_rank.decode('utf-8')
        if isinstance(self.sum_score, bytes):
            self.sum_score = int(self.sum_score)
        if isinstance(self.handicap_score, bytes):
            self.handicap_score = int(self.handicap_score)
        if isinstance(self.is_group_win, bytes):
            self.is_group_win = bool(int(self.is_group_win))
        if isinstance(self.is_group_win_handicap, bytes):
            self.is_group_win_handicap = bool(int(self.is_group_win_handicap))
        if isinstance(self.hole_number, bytes):
            self.hole_number = int(self.hole_number)
        if isinstance(self.score, bytes):
            self.score = int(self.score)


@dataclass
class ParticipantRedisData:
    participant_id: int
    group_type: chr
    team_type: chr
    is_group_win: Optional[bool]
    is_group_win_handicap: Optional[bool]
    sum_score: int
    handicap_score: int

    def __post_init__(self):
        # 필드들이 bytes 타입인 경우 적절한 타입으로 변환
        if isinstance(self.participant_id, bytes):
            self.participant_id = int(self.participant_id)
        if isinstance(self.group_type, bytes):
            self.group_type = self.group_type.decode('utf-8')
        if isinstance(self.team_type, bytes):
            self.team_type = self.team_type.decode('utf-8')
        if isinstance(self.is_group_win, bytes):
            self.is_group_win = bool(int(self.is_group_win))
        if isinstance(self.is_group_win_handicap, bytes):
            self.is_group_win_handicap = bool(int(self.is_group_win_handicap))
        if isinstance(self.sum_score, bytes):
            self.sum_score = int(self.sum_score)
        if isinstance(self.handicap_score, bytes):
            self.handicap_score = int(self.handicap_score)