"""
2024.08.28
utils/assign_ranks.py

참가자들의 순위를 할당하는 함수
"""

@staticmethod
def assign_ranks(participants, rank_type):
    """
    participants 리스트를 정렬된 순서로 받아, 해당 기준으로 순위를 할당.
    rank_type에 따라 일반 rank 또는 handicap_rank를 설정.
    """
    previous_score = None
    rank = 1
    tied_rank = 1  # 동점자의 랭크를 별도로 관리
    rank_field = rank_type

    for idx, participant in enumerate(participants):
        # 동적으로 rank와 handicap_rank 속성을 추가
        if not hasattr(participant, 'rank'):
            participant.rank = None
        if not hasattr(participant, 'handicap_rank'):
            participant.handicap_rank = None

        current_score = getattr(participant, rank_type.replace('rank', 'score'))
        # 순위 할당
        if current_score == previous_score:
            setattr(participant, rank_field, f"T{tied_rank}")  # 이전 참가자와 동일한 점수라면 T로 표기
            setattr(participants[idx - 1], rank_field, f"T{tied_rank}")  # 이전 참가자의 랭크도 T로 업데이트
        else:
            setattr(participant, rank_field, str(rank))  # 새로운 점수일 경우 일반 순위
            tied_rank = rank  # 새로운 점수에서 동점 시작 지점을 설정

        previous_score = current_score
        rank += 1  # 다음 순위로 이동
        participant.save()