'''
MVP demo ver 0.0.3
2024.08.23
participa/stroke/redis_interface.py

- Redis 데이터베이스와 상호작용하는 클래스
- 참가자와 이벤트의 데이터를 관리
'''
from dataclasses import asdict
import json
import logging
from multiprocessing.pool import AsyncResult

from asgiref.sync import sync_to_async
from participants.tasks import save_event_periodically_task
import redis

from golbang import settings
from participants.models import Participant
from participants.stroke.data_class import EventData, ParticipantRedisData

# Redis 클라이언트 설정
redis_client = redis.StrictRedis(
    host='redis', 
    port=6379, 
    db=0, 
    password=settings.REDIS_PASSWORD,
    decode_responses=True,  # 문자열 바로 디코딩되게
    socket_connect_timeout=5,
    socket_timeout=5
)

class RedisInterface:
    def __init__(self):
        self.redis_client = redis_client  # <-- 여기 정의해야 함

    async def decrease_event_auto_migration_count(self, event_id):
        key = f"event:{event_id}:is_saving"
        count = await sync_to_async(redis_client.decr)(key)
        logging.info(f"참가자: {count} 감소")

        if count <= 0:
            await sync_to_async(redis_client.delete)(key)
            logging.info(f"[{event_id}] 모든 참가자 퇴장 → count 보관 키 삭제")
    
    
    async def save_celery_event_from_redis_to_mysql(self, event_id, is_count_incr = True):
        '''
        key가 레디스에 저장돼있으면,
        redis에서 mysql로 정기적(xx초 간격)으로 마이그레이션 되는 것을 의미
        task_key는 celery 작업 상태 추적키
        '''
        key = f"event:{event_id}:is_saving"
        task_key = f"{key}:task_id"

        # 1️⃣ 먼저 task_key 존재 + 상태 확인
        if await sync_to_async(redis_client.exists)(task_key):
            task_id = await sync_to_async(redis_client.get)(task_key)
            if task_id:
                result = AsyncResult(task_id)
                if result.status in ['PENDING', 'STARTED']:
                    # ✅ 현재 Celery 작업이 진행 중이면 → key만 다시 세팅
                    await sync_to_async(redis_client.setnx)(key, 1)
                    await sync_to_async(redis_client.expire)(key, 1800)
                    logging.info(f"[{event_id}] 기존 Celery task 실행 중 → key만 재설정")
                    return
                else:
                    # ✅ 종료된 task → task_key 제거
                    logging.info(f"[{event_id}] 기존 Celery task 종료됨 → task_key 삭제")
                    await sync_to_async(redis_client.delete)(task_key)
                    
        # task_key가 없으면 새로 생성
        task_set = await sync_to_async(redis_client.setnx)(task_key, "creating")

        if task_set:
            task = save_event_periodically_task.delay(event_id)
            await sync_to_async(redis_client.set)(task_key, task.id)
            await sync_to_async(redis_client.expire)(task_key, 86400) # 하루 동안 유지

        # 2️⃣ 여기까지 왔으면 → 새 작업 실행 가능
        created = await sync_to_async(redis_client.setnx)(key, 1)

        if created:
            # ✅ 처음 생성된 경우 → Celery Task 시작
            logging.info(f"[{event_id}] 마이그레이션 기본키 생성")
            await sync_to_async(redis_client.expire)(key, 1800) # 30분 동안 유지
        elif is_count_incr:
            # 이미 존재하는 경우, count 증가 (count 0이면 키 제거)
            logging.info(f"[{event_id}] 이미 마이그레이션 중 → count 증가")
            await sync_to_async(redis_client.incr)(key)
            await sync_to_async(redis_client.expire)(key, 1800) # 30분 갱신
        else:
            logging.info(f"[{event_id}] 이미 마이그레이션 중 → 기본키 유효기간 갱신")
            await sync_to_async(redis_client.expire)(key, 1800) # 30분 갱신



    async def save_participant_in_redis(self, participant: Participant):
        # 참가자 Redis 캐싱 메서드
        key = f'event:{participant.event.pk}:participant:{participant.pk}'
        value = ParticipantRedisData.orm_to_participant_redis(participant=participant).to_redis_dict()

        await sync_to_async(redis_client.hset)(key, mapping=value)  # 문자열로 저장
        await sync_to_async(redis_client.expire)(key, 172800)       # 2일 TTL 설정
        data = await sync_to_async(redis_client.hgetall)(key)

        return ParticipantRedisData(**data)  # 저장된 값을 반환

    async def get_participant_from_redis(self, event_id, participant_id):
        if event_id is None:
            # Redis에서 해당 participant_id에 해당하는 모든 키 탐색
            keys = await sync_to_async(redis_client.keys)(f'event:*:participant:{participant_id}')
            if not keys:
                return None
            key = keys[0]
        else:
            key = f'event:{event_id}:participant:{participant_id}'

        data = await sync_to_async(redis_client.hgetall)(key)
        print(f"Redis에서 참가자 정보 가져옴: {data}")
        if data:
            return ParticipantRedisData(**data)
        return None

    async def update_hole_score_in_redis(self, participant_id, hole_number, score):
        # Redis에 홀 점수를 업데이트
        key = f'participant:{participant_id}:hole:{hole_number}'
        await sync_to_async(redis_client.set)(key, score)
        await sync_to_async(redis_client.expire)(key, 172800)

    async def update_participant_sum_and_handicap_score_in_redis(self, participant: ParticipantRedisData):
        # Redis에 참가자의 총 점수와 핸디캡 점수를 업데이트
        keys_pattern = f'participant:{participant.participant_id}:hole:*'
        keys = await sync_to_async(redis_client.keys)(keys_pattern)

        sum_score = 0
        for key in keys:
            score = await sync_to_async(redis_client.get)(key)
            if score is not None:
                sum_score += int(score)
        handicap_score = sum_score - participant.user_handicap
        redis_key = f'event:{participant.event_id}:participant:{participant.participant_id}'
        await sync_to_async(redis_client.hset)(redis_key, mapping={
            "sum_score": sum_score,
            "handicap_score": handicap_score,
        })

    async def update_rankings_in_redis(self, event_id):
        # Redis에 참가자들의 순위를 업데이트

        participants = await self.get_event_participants_from_redis(event_id)

        # sum_score이 0인 참가자들은 제외
        participants = [p for p in participants if p.sum_score != 0]

        sorted_by_sum_score = sorted(participants, key=lambda p: p.sum_score)
        sorted_by_handicap_score = sorted(participants, key=lambda p: p.handicap_score)

        self.assign_ranks(sorted_by_sum_score, 'sum_rank')
        self.assign_ranks(sorted_by_handicap_score, 'handicap_rank')

        for participant in participants:
            redis_key = f'event:{event_id}:participant:{participant.participant_id}'
            await sync_to_async(redis_client.hset)(redis_key, "rank", participant.rank)
            await sync_to_async(redis_client.hset)(redis_key, "handicap_rank", participant.handicap_rank)

    def assign_ranks(self, participants, rank_type):
        """
        participants 리스트를 정렬된 순서로 받아, 해당 기준으로 순위를 할당.
        rank_type에 따라 일반 rank 또는 handicap_rank를 설정.
        """
        previous_score = None
        rank = 1
        tied_rank = 1  # 동점자의 랭크를 별도로 관리
        rank_field = 'rank' if rank_type == 'sum_rank' else 'handicap_rank'

        logging.info(f'===={rank_type}====')
        for idx, participant in enumerate(participants):
            logging.info(f'participant{idx}: {participant}')
            # 동적으로 rank와 handicap_rank 속성을 추가
            if not hasattr(participant, 'rank'):
                participant.rank = None
            if not hasattr(participant, 'handicap_rank'):
                participant.handicap_rank = None

            current_score = getattr(participant, rank_type.replace('rank', 'score'))
            logging.info(f'previous_score: {previous_score}, current_score: {current_score}')
            # 순위 할당
            if current_score == previous_score:
                setattr(participant, rank_field, f"T{tied_rank}")  # 이전 참가자와 동일한 점수라면 T로 표기
                logging.info(f'current P: rank: {participant.rank}, handicap_rank: {participant.handicap_rank}')
                setattr(participants[idx - 1], rank_field, f"T{tied_rank}")  # 이전 참가자의 랭크도 T로 업데이트
                logging.info(
                    f'previous P: rank: {participants[idx - 1].rank}, handicap_rank: {participants[idx - 1].handicap_rank}')

            else:
                setattr(participant, rank_field, str(rank))  # 새로운 점수일 경우 일반 순위
                logging.info(f'current P: rank: {participant.rank}, handicap_rank: {participant.handicap_rank}')
                tied_rank = rank  # 새로운 점수에서 동점 시작 지점을 설정

            previous_score = current_score
            rank += 1  # 다음 순위로 이동
    
    async def get_event_participants_from_redis(self, event_id, group_type_filter=None):
        base_key = f'event:{event_id}:participant:'
        cursor = 0
        keys = []

        while True:
            cursor, scanned_keys = await sync_to_async(redis_client.scan)(
                cursor=cursor,
                match=f'{base_key}*',
                count=100
            )
            keys.extend(scanned_keys)
            if cursor == 0:
                break

        participants = []
        for key in keys:
            try:
                participant_id = key.split(':')[-1]
                participant_key = f'{base_key}{participant_id}'
                data = await sync_to_async(redis_client.hgetall)(participant_key)

                if not data:
                    continue

                participant_data = ParticipantRedisData(**data)
                participants.append(participant_data)

            except Exception as e:
                logging.warning(f"Failed to parse participant from key {key}: {e}")
                continue

        return participants


    async def get_group_participants_from_redis(self, event_id, group_type_filter=None):
        # Redis에서 참가자들을 가져옴

        event_participants = await self.get_event_participants_from_redis(event_id, group_type_filter)
        if group_type_filter is None:
            return event_participants
        
        # group_type 기준으로 필터링
        filtered = [
            p for p in event_participants
            if getattr(p, "group_type", None) == group_type_filter
        ]

        return filtered
    
    async def update_is_group_win_in_redis(self, participant):
        event_id = participant.event_id

        # 각 조별로 점수를 계산하여 Redis에 조별 승리 여부를 저장하는 로직
        group_participants = await self.get_group_participants_from_redis(event_id, participant.group_type)
        logging.info('group_participants: %s', group_participants)
        # 팀별로 점수 계산
        team_a_score = sum([p.sum_score for p in group_participants if p.team_type == Participant.TeamType.TEAM1])
        logging.info(f'team_a_score: {team_a_score}')
        team_b_score = sum([p.sum_score for p in group_participants if p.team_type == Participant.TeamType.TEAM2])
        logging.info(f'team_b_score: {team_b_score}')

        is_team_a_winner = int(team_a_score < team_b_score)
        is_team_b_winner = int(team_b_score < team_a_score)

        # 팀별로 핸디캡 점수 계산
        handicap_a_score = sum([p.handicap_score for p in group_participants if p.team_type == Participant.TeamType.TEAM1])
        logging.info(f'handicap_a_score: {handicap_a_score}')
        handicap_b_score = sum([p.handicap_score for p in group_participants if p.team_type == Participant.TeamType.TEAM2])
        logging.info(f'handicap_b_score: {handicap_b_score}')

        is_handicap_a_winner = int(handicap_a_score < handicap_b_score)
        is_handicap_b_winner = int(handicap_b_score < handicap_a_score)

        # Redis에 저장
        for p in group_participants:
            redis_key = f'event:{event_id}:participant:{p.participant_id}'
            await sync_to_async(redis_client.hset)(redis_key, "is_group_win", is_team_a_winner
                                                    if p.team_type == Participant.TeamType.TEAM1 else is_team_b_winner)
            await sync_to_async(redis_client.hset)(redis_key, "is_group_win_handicap",is_handicap_a_winner
                                                    if p.team_type == Participant.TeamType.TEAM1 else is_handicap_b_winner)
            await sync_to_async(redis_client.expire)(redis_key, 172800)

    async def update_event_win_team_in_redis(self, event_id):
        # 이벤트 전체의 승리 팀을 결정하여 Redis에 저장하는 로직
        participants = await self.get_participants_from_redis(event_id)
        event_key = f'event:{event_id}'

        # 그룹별 승리팀 결정
        a_team_wins = len([p for p in participants if p.team_type == Participant.TeamType.TEAM1 and p.is_group_win])
        logging.info(f'a_team_wins: {a_team_wins}')
        b_team_wins = len([p for p in participants if p.team_type == Participant.TeamType.TEAM2 and p.is_group_win])
        logging.info(f'b_team_wins: {b_team_wins}')

        group_win_team = 'A' if a_team_wins > b_team_wins else 'B' if b_team_wins > a_team_wins else 'DRAW'
        await sync_to_async(redis_client.hset)(event_key, "group_win_team", group_win_team)

        # 그룹별 핸디캡 승리팀 결정
        a_team_wins_handicap = len(
            [p for p in participants if p.team_type == Participant.TeamType.TEAM1 and p.is_group_win_handicap])
        b_team_wins_handicap = len(
            [p for p in participants if p.team_type == Participant.TeamType.TEAM2 and p.is_group_win_handicap])

        group_win_team_handicap = 'A' if a_team_wins_handicap > b_team_wins_handicap else 'B' if b_team_wins_handicap > a_team_wins_handicap else 'DRAW'
        await sync_to_async(redis_client.hset)(event_key, "group_win_team_handicap", group_win_team_handicap)

        # 전체 승리팀 결정
        a_team_total_score = sum([p.sum_score for p in participants if p.team_type == Participant.TeamType.TEAM1])
        b_team_total_score = sum([p.sum_score for p in participants if p.team_type == Participant.TeamType.TEAM2])

        total_win_team = 'A' if a_team_total_score < b_team_total_score else 'B' if b_team_total_score < a_team_total_score else 'DRAW'
        await sync_to_async(redis_client.hset)(event_key, "total_win_team", total_win_team)

        # 전체 핸디캡 승리팀 결정
        a_team_total_handicap_score = sum(
            [p.handicap_score for p in participants if p.team_type == Participant.TeamType.TEAM1])
        b_team_total_handicap_score = sum(
            [p.handicap_score for p in participants if p.team_type == Participant.TeamType.TEAM2])

        total_win_team_handicap = 'A' if a_team_total_handicap_score < b_team_total_handicap_score else 'B' if b_team_total_handicap_score < a_team_total_handicap_score else 'DRAW'
        await sync_to_async(redis_client.hset)(event_key, "total_win_team_handicap", total_win_team_handicap)

        await sync_to_async(redis_client.expire)(event_key, 172800)

    async def get_all_hole_scores_from_redis(self, participant_id):
        # Redis에서 모든 홀 점수를 가져옴

        logging.info('participant_id: %s', participant_id)
        keys_pattern = f'participant:{participant_id}:hole:*'
        keys = await sync_to_async(redis_client.keys)(keys_pattern)
        hole_scores = []
        for key in keys:
            logging.info('hole_scores: %s', hole_scores)
            hole_number = int(key.split(':')[-1])
            score = int(await sync_to_async(redis_client.get)(key))
            logging.info('score: %s', score)
            hole_scores.append({'hole_number': hole_number, 'score': score})
        return hole_scores

    async def get_event_data_from_redis(self, event_id):
        # Redis에서 이벤트 데이터를 가져옴

        redis_key = f'event:{event_id}'
        event_data_dict = await sync_to_async(redis_client.hgetall)(redis_key)

        # EventData 클래스에 필드를 전달할 때 기본값을 설정하지 않으면 Optional 처리해주고, 디코딩은 __post_init__에서 처리
        return EventData(
            group_win_team=event_data_dict.get("group_win_team"),
            group_win_team_handicap=event_data_dict.get("group_win_team_handicap"),
            total_win_team=event_data_dict.get("total_win_team"),
            total_win_team_handicap=event_data_dict.get("total_win_team_handicap")
        )