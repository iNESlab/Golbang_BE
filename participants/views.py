'''
MVP demo ver 0.0.8
2024.08.02
participants/views.py

역할: Django Rest Framework(DRF)를 사용하여 이벤트 API 엔드포인트의 로직을 처리
- 참가자 : 자신의 참가 상태를 변경
'''
from django.db.models import Avg, Min, Count
from datetime import datetime, timedelta

from rest_framework import status
from rest_framework.decorators import permission_classes, action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import viewsets

from participants.models import Participant
from participants.serializers import ParticipantCreateUpdateSerializer
from utils.error_handlers import handle_400_bad_request, handle_404_not_found, handle_401_unauthorized

@permission_classes([IsAuthenticated])
class ParticipantViewSet(viewsets.ModelViewSet):
    queryset = Participant.objects.all()
    serializer_class = ParticipantCreateUpdateSerializer

    def partial_update(self, request, *args, **kwargs):
        try:
            user = self.request.user
            status_type = self.request.query_params.get('status_type')
            if status_type not in Participant.StatusType.__members__:
                return handle_400_bad_request(f'status_type: {status_type} 이 잘못되었습니다.  '
                                              f'올바른 status_type : ACCEPT, PARTY, DENY, PENDING')

            participant = Participant.objects.get(pk=kwargs['pk'])

            find_user=participant.club_member.user # 참가자에 대한 사용자 정보
            if not find_user == user:
                return handle_401_unauthorized(f'해당 참가자({find_user.name})가 아닙니다.')

            participant.status_type = status_type   # 상태 타입 업데이트
            participant.save()

            serializer = ParticipantCreateUpdateSerializer(participant)

            response_data = {
                'status': status.HTTP_200_OK,
                'message': 'Successfully participant status_type update',
                'data': serializer.data
            }
            return Response(response_data, status=status.HTTP_200_OK)
        except Participant.DoesNotExist: # 참가자가 존재하지 않을 경우
            return handle_404_not_found('participant', kwargs['pk'])
        except Exception as e: # 기타 예외 처리
            return handle_400_bad_request({'error': str(e)})


class StatisticsViewSet(viewsets.ViewSet):
    '''
    참가자 개인 통계 클래스
    '''
    permission_classes = [IsAuthenticated]

    def list(self, request):
        '''
        사용 가능한 통계 API의 목록을 반환
        '''
        return Response({
            "status": status.HTTP_200_OK,
            "message": "Statistics API root",
            "data": {
                "endpoints": {
                    "overall": "GET /participants/statistics/overall/",
                    "yearly": "GET /participants/statistics/yearly/{year}/",
                    "period": "GET /participants/statistics/period/?start_date={start_date}&end_date={end_date}",
                    "ranks": "GET /clubs/statistics/ranks/?club_id={club_id}",
                    "events": "GET /clubs/statistics/events/?club_id={club_id}",
                }
            }
        })

    @action(detail=False, methods=['get'], url_path='overall')
    def overall_statistics(self, request):
        '''
        전체 통계
        GET /participants/statistics/overall/
        '''
        user = request.user  # 요청을 보낸 사용자를 가져옴
        participants = Participant.objects.filter(club_member__user=user)  # 해당 사용자의 모든 참가 데이터

        if not participants.exists():  # 참가 데이터가 없을 경우, 404
            return handle_404_not_found('participant data', 'for the user')

        # 평균 스코어 계산
        average_score = participants.aggregate(average=Avg('sum_score'))['average'] or 0

        # 베스트 스코어 (최소 스코어) 계산
        best_score = participants.aggregate(best=Min('sum_score'))['best'] or 0

        # 핸디캡 적용 베스트 스코어 (최소 핸디캡 스코어) 계산
        handicap_bests_score = participants.aggregate(best=Min('handicap_score'))['best'] or 0

        # 총 라운드 수 계산
        games_played = participants.count()

        # 응답 데이터 생성
        data = {
            "average_score": round(average_score, 1),
            "best_score": best_score,
            "handicap_bests_score": handicap_bests_score,
            "games_played": games_played
        }

        return Response({
            "status": status.HTTP_200_OK,
            "message": "Successfully retrieved overall statistics",
            "data": data
        }, status=status.HTTP_200_OK)

    @action(detail=False, methods=['get'], url_path='yearly/(?P<year>[0-9]{4})') # 0~9까지 4자리 수
    def yearly_statistics(self, request, year=None):
        '''
        연도별 통계 조회
        GET /participants/statistics/yearly/{year}/
        '''
        user = request.user
        participants = Participant.objects.filter(club_member__user=user,
                                                  event__start_date_time__year=year)  # 특정 연도의 참가 데이터

        if not participants.exists():  # 해당 연도의 참가 데이터가 없을 경우
            return handle_404_not_found('participant data for the year', year)

        # 평균 스코어 계산
        average_score = participants.aggregate(average=Avg('sum_score'))['average'] or 0

        # 베스트 스코어 (최소 스코어) 계산
        best_score = participants.aggregate(best=Min('sum_score'))['best'] or 0

        # 핸디캡 적용 베스트 스코어 (최소 핸디캡 스코어) 계산
        handicap_bests_score = participants.aggregate(best=Min('handicap_score'))['best'] or 0

        # 총 라운드 수 계산
        games_played = participants.count()

        # 응답 데이터 생성
        data = {
            "year": year,
            "average_score": round(average_score, 1),
            "best_score": best_score,
            "handicap_bests_score": handicap_bests_score,
            "games_played": games_played
        }

        return Response({
            "status": status.HTTP_200_OK,
            "message": f"Successfully retrieved statistics for the year {year}",
            "data": data
        }, status=status.HTTP_200_OK)

    @action(detail=False, methods=['get'], url_path='period')
    def period_statistics(self, request):
        '''
        기간별 통계 조회
        GET /participants/statistics/period/?start_date={start_date}&end_date={end_date}
        '''
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')

        if not start_date or not end_date:  # 날짜가 제공되지 않은 경우 400
            return Response({
                "status": status.HTTP_400_BAD_REQUEST,
                "message": "start_date and end_date query parameters are required."
            }, status=status.HTTP_400_BAD_REQUEST)

        # 날짜를 datetime 객체로 변환
        start_date = datetime.strptime(start_date, '%Y-%m-%d')
        end_date = datetime.strptime(end_date, '%Y-%m-%d')

        # end_date를 다음 날로 설정하여 해당 날짜의 끝까지 포함
        end_date = end_date + timedelta(days=1) - timedelta(seconds=1)

        user = request.user
        participants = Participant.objects.filter( # 특정 날짜 범위 내의 참가 데이터
            club_member__user=user,
            event__start_date_time__range=[start_date, end_date + timedelta(days=1)] # 범위 지정할 때에 2번째 인자는 미만으로 처리되므로 end_date에 +1
        )

        if not participants.exists():  # 해당 기간에 대한 참가 데이터가 없을 경우
            return handle_404_not_found('participant data for the given period', f"{start_date} to {end_date}")

        # 평균 스코어 계산
        average_score = participants.aggregate(average=Avg('sum_score'))['average'] or 0

        # 베스트 스코어 (최소 스코어) 계산
        best_score = participants.aggregate(best=Min('sum_score'))['best'] or 0

        # 핸디캡 적용 베스트 스코어 (최소 핸디캡 스코어) 계산
        handicap_bests_score = participants.aggregate(best=Min('handicap_score'))['best'] or 0

        # 총 라운드 수 계산
        games_played = participants.count()

        # 응답 데이터 생성
        data = {
            "start_date": start_date.strftime('%Y-%m-%d'),
            "end_date": (end_date - timedelta(seconds=1)).strftime('%Y-%m-%d'),
            "average_score": round(average_score, 1),
            "best_score": best_score,
            "handicap_bests_score": handicap_bests_score,
            "games_played": games_played
        }

        return Response({
            "status": status.HTTP_200_OK,
            "message": f"Successfully retrieved statistics for the period {start_date} to {end_date}",
            "data": data
        }, status=status.HTTP_200_OK)
