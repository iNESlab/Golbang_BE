'''
MVP demo ver 0.0.8
2024.08.28
participants/utils/statistics.py

역할: 참가자의 개인 통계를 구할 때의 공통 기능 함수
- 평균 스코어 계산, 베스트 스코어, 핸디캡 적용 베스트 스코어, 총 라운드 수 계산
'''

from datetime import timedelta
from django.db.models import Avg, Min

def calculate_statistics(participants, start_date=None, end_date=None, year=None):
    """
    통계 데이터를 계산하고 응답 데이터를 생성하는 함수
    에러 발생 시 None과 에러 메시지를 반환
    """
    if not participants.exists():
        if year:
            return None, ('participant data for the year', year)
        elif start_date and end_date:
            return None, ('participant data for the given period', f"{start_date} to {end_date}")
        else:
            return None, ('participant data', 'for the user')

    # 평균 스코어 계산
    average_score = participants.aggregate(average=Avg('sum_score'))['average'] or 0

    # 베스트 스코어 (최소 스코어) 계산
    best_score = participants.aggregate(best=Min('sum_score'))['best'] or 0

    # 핸디캡 적용 베스트 스코어 (최소 핸디캡 스코어) 계산
    handicap_bests_score = participants.aggregate(best=Min('handicap_score'))['best'] or 0

    # 총 라운드 수 계산
    games_played = participants.count()

    # 응답 데이터 초기화
    data = {}
    if year:
        data["year"] = year
    if start_date and end_date:
        data["start_date"] = start_date.strftime('%Y-%m-%d')
        data["end_date"] = (end_date - timedelta(seconds=1)).strftime('%Y-%m-%d')

    # 응답 데이터에 통계 데이터 추가
    data.update( {
        "average_score": round(average_score, 1),
        "best_score": best_score,
        "handicap_bests_score": handicap_bests_score,
        "games_played": games_played
    } )

    return data, None