import logging

from asgiref.sync import sync_to_async
import redis

from participants.models import Participant
from participants.stroke.data_class import EventData

# Redis 클라이언트 설정
redis_client = redis.StrictRedis(host='redis', port=6379, db=0)


class RedisInterface:

    async def update_hole_score_in_redis(self, participant_id, hole_number, score):
        key = f'participant:{participant_id}:hole:{hole_number}'
        await sync_to_async(redis_client.set)(key, score)
        await sync_to_async(redis_client.expire)(key, 259200)

    async def update_participant_sum_and_handicap_score_in_redis(self, participant):
        keys_pattern = f'participant:{participant.id}:hole:*'
        keys = await sync_to_async(redis_client.keys)(keys_pattern)

        sum_score = 0
        for key in keys:
            score = await sync_to_async(redis_client.get)(key)
            sum_score += int(score)
        event_id = participant.event_id
        handicap_score = sum_score - participant.club_member.user.handicap
        redis_key = f'event:{event_id}:participant:{participant.id}'
        await sync_to_async(redis_client.hset)(redis_key, "sum_score", sum_score)
        await sync_to_async(redis_client.hset)(redis_key, "handicap_score", handicap_score)
        await sync_to_async(redis_client.hset)(redis_key, "group_type", participant.group_type)
        await sync_to_async(redis_client.hset)(redis_key, "team_type", participant.team_type)

    async def update_rankings_in_redis(self, event_id):
        participants = await self.get_participants_from_redis(event_id)

        sorted_by_sum_score = sorted(participants, key=lambda p: p.sum_score)
        sorted_by_handicap_score = sorted(participants, key=lambda p: p.handicap_score)

        self.assign_ranks(sorted_by_sum_score, 'sum_rank')
        self.assign_ranks(sorted_by_handicap_score, 'handicap_rank')

        for participant in participants:
            redis_key = f'event:{event_id}:participant:{participant.id}'
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

    async def get_scores_from_redis(self, participant):
        redis_key = f'event:{participant.event_id}:participant:{participant.id}'
        sum_score = await sync_to_async(redis_client.hget)(redis_key, "sum_score")
        handicap_score = await sync_to_async(redis_client.hget)(redis_key, "handicap_score")

        is_group_win = await sync_to_async(redis_client.hget)(redis_key, "is_group_win")
        is_group_win_handicap = await sync_to_async(redis_client.hget)(redis_key, "is_group_win_handicap")

        sum_score = int(sum_score) if sum_score else 0
        handicap_score = int(handicap_score) if handicap_score else 0
        is_group_win = bool(int(is_group_win)) if is_group_win else False
        is_group_win_handicap = bool(int(is_group_win)) if is_group_win_handicap else False

        return sum_score, handicap_score, is_group_win, is_group_win_handicap

    async def get_participants_from_redis(self, event_id, group_type_filter=None):
        base_key = f'event:{event_id}:participant:'
        keys = await sync_to_async(redis_client.keys)(f'{base_key}*')
        logging.info(f'keys:{keys}')
        participants = []

        for key in keys:
            participant_id = key.decode('utf-8').split(':')[-1]
            logging.info(f'====participant_id:{participant_id}====')
            participant_key = f'{base_key}{participant_id}'

            # hgetall로 모든 데이터를 한 번에 가져옴
            participant_data = await sync_to_async(redis_client.hgetall)(participant_key)

            # 각 필드를 가져와 변환
            sum_score = participant_data.get(b'sum_score', 0)
            handicap_score = participant_data.get(b'handicap_score', 0)
            team_type = participant_data.get(b'team_type', b'')
            group_type = participant_data.get(b'group_type', 0)
            is_group_win = participant_data.get(b'is_group_win', b'0')
            is_group_win_handicap = participant_data.get(b'is_group_win_handicap', b'0')

            logging.info(f'group_type:{int(group_type)}, group_type_filter:{group_type_filter}')
            # 그룹 필터링: group_type이 전달되었고, 가져온 group_type이 동일한지 확인
            if group_type_filter is not None and group_type and int(group_type) != group_type_filter:
                continue

            participant = Participant(
                id=participant_id,
                event_id=event_id,
                sum_score=int(sum_score) if sum_score else 0,
                handicap_score=int(handicap_score) if handicap_score else 0,
                team_type=team_type.decode('utf-8') if team_type else None, # 문자열은 디코딩 해줘야함. 정수는 int로 됨
                group_type=int(group_type) if group_type else None,
                is_group_win=bool(int(is_group_win)) if is_group_win else False,
                is_group_win_handicap=bool(int(is_group_win_handicap)) if is_group_win_handicap else False
            )

            participants.append(participant)

        return participants

    async def update_is_group_win_in_redis(self, participant):
        event_id = participant.event_id

        # 각 조별로 점수를 계산하여 Redis에 조별 승리 여부를 저장하는 로직
        group_participants = await self.get_participants_from_redis(event_id, participant.group_type)
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
            redis_key = f'event:{event_id}:participant:{p.id}'
            await sync_to_async(redis_client.hset)(redis_key, "is_group_win", is_team_a_winner
                                                    if p.team_type == Participant.TeamType.TEAM1 else is_team_b_winner)
            await sync_to_async(redis_client.hset)(redis_key, "is_group_win_handicap",is_handicap_a_winner
                                                    if p.team_type == Participant.TeamType.TEAM1 else is_handicap_b_winner)

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

    async def get_all_hole_scores_from_redis(self, participant_id):
        logging.info('participant_id: %s', participant_id)
        keys_pattern = f'participant:{participant_id}:hole:*'
        keys = await sync_to_async(redis_client.keys)(keys_pattern)
        hole_scores = []
        for key in keys:
            logging.info('hole_scores: %s', hole_scores)
            hole_number = int(key.decode('utf-8').split(':')[-1])
            score = int(await sync_to_async(redis_client.get)(key))
            logging.info('score: %s', score)
            hole_scores.append({'hole_number': hole_number, 'score': score})
        return hole_scores

    async def get_event_data_from_redis(self, event_id):
        redis_key = f'event:{event_id}'
        event_data_dict = await sync_to_async(redis_client.hgetall)(redis_key)

        # EventData 클래스에 필드를 전달할 때 기본값을 설정하지 않으면 Optional 처리해주고, 디코딩은 __post_init__에서 처리
        return EventData(
            group_win_team=event_data_dict.get(b"group_win_team"),
            group_win_team_handicap=event_data_dict.get(b"group_win_team_handicap"),
            total_win_team=event_data_dict.get(b"total_win_team"),
            total_win_team_handicap=event_data_dict.get(b"total_win_team_handicap")
        )