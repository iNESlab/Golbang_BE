'''
MVP demo ver 0.0.9
2024.08.28
clubs/utils.py

역할: 클럽 내 공통 기능 또는 특정 기능 함수화
'''
from participants.models import Participant


# clubs/utils.py

def calculate_event_points(event_id):
    """
    이벤트의 모든 참가자에 대해 포인트를 계산
    """
    participants = Participant.objects.filter(event_id=event_id).order_by('sum_score')

    total_participants = participants.count()
    points = {}
    rank = 1

    for idx, participant in enumerate(participants):
        # 같은 순위의 경우 동일한 점수를 부여
        if idx > 0 and participant.sum_score > participants[idx - 1].sum_score:
            rank = idx + 1

        points[participant.id] = total_participants - rank + 1  # 높은 순위일수록 높은 점수
        points[participant.id] += 2  # 참석 점수 추가

    return points
