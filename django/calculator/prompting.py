import os
import uuid
import math
import tempfile
from typing import Iterable, List, Sequence

import numpy as np
import pandas as pd
from django.conf import settings

from utils.tempfile_helpers import handle_uploaded_file



def _parse_selected_holes(selected_holes) -> np.ndarray:
    """
    selected_holes 가
      - '1,3,5,...' (문자열) 이거나
      - [1,3,5,...] (1-indexed 정수 리스트) 이거나
      - [0,2,4,...] (0-indexed 정수 리스트)
    어떤 형태로 와도 0-index numpy 배열로 변환해서 반환.
    """
    if selected_holes is None:
        raise ValueError("selected_holes 가 필요합니다(12개).")

    if isinstance(selected_holes, str):
        parts = [p.strip() for p in selected_holes.split(",") if p.strip() != ""]
        ints = [int(p) for p in parts]
    elif isinstance(selected_holes, Iterable):
        ints = [int(x) for x in selected_holes]
    else:
        raise ValueError(f"selected_holes 타입이 잘못되었습니다: {type(selected_holes)}")

    # 1-index → 0-index 정규화
    arr = np.array(ints, dtype=int)
    if arr.min() >= 1:
        arr = arr - 1

    if arr.ndim != 1 or len(arr) != 12:
        raise ValueError(f"선택 홀은 정확히 12개여야 합니다. 현재: {len(arr)}개")

    return arr


def _to_float_or_nan(x) -> float:
    """엑셀에서 온 None/''/공백/문자 등을 안전하게 float로 변환"""
    if x is None:
        return np.nan
    if isinstance(x, (int, float, np.number)):
        return float(x)
    if isinstance(x, str):
        s = x.strip()
        if not s:
            return np.nan
        try:
            return float(s)
        except ValueError:
            return np.nan
    try:
        return float(x)
    except Exception:
        return np.nan


def calculate_sneperio(
    scores_by_player: List[List[float]],
    par_values: Sequence[float],
    designated_idxs: Sequence[int],
) -> List[object]:
    """
    scores_by_player: [ [H1..H18], [H1..H18], ... ]  (각 내포 리스트 길이 18)
      - 각 값은 "par 대비 스코어(±)" 라는 현재 시트 구조 가정에 맞춤.
    par_values: 길이 18
    designated_idxs: 길이 12, 0-index
    반환: [신페리오 핸디캡(소수1자리) 또는 빈 문자열]  (직렬화 안전)
    """
    par = np.asarray(par_values, dtype=float)
    idx = np.asarray(designated_idxs, dtype=int)

    out: List[object] = []
    for row in scores_by_player:
        arr = np.array([_to_float_or_nan(v) for v in row], dtype=float)
        part = arr[idx]
        par_part = par[idx]

        # 지정 12홀 중 하나라도 NaN이면 빈 문자열 반환(정책에 맞게 조정 가능)
        if np.isnan(part).any():
            out.append("")
            continue

        score_sum = float(np.nansum(part))
        par_sum   = float(np.nansum(par_part))
        snep = (((score_sum + par_sum) * 1.5) - 72.0) * 0.8
        out.append(round(snep, 1))
    return out


# ----- 엑셀 파싱 도우미 -----

def _extract_scores_matrix(df: pd.DataFrame) -> np.ndarray:
    """
    엑셀에서 'hole' (대/소문자 무관)이 들어간 첫 열 라벨을 가진 행들을 점수로 간주.
    반환: shape = (18, N_players) 의 float 배열 (NaN 포함 가능)
    """
    # 첫 컬럼에 'hole' 포함된 행만 (case-insensitive)
    mask = df.iloc[:, 0].astype(str).str.contains("hole", case=False, na=False)
    score_rows = df.loc[mask]

    if score_rows.empty:
        raise ValueError("엑셀에서 'hole' 행을 찾을 수 없습니다. 첫 열에 hole 라벨이 있어야 합니다.")

    # 첫 열(라벨) 제외 → (rows, players)
    score_values = score_rows.iloc[:, 1:].applymap(_to_float_or_nan).values

    # 홀 수 검증 (18홀 아니면 에러)
    if score_values.shape[0] != 18:
        raise ValueError(f"18홀이 아닙니다. 현재 hole 행 수: {score_values.shape[0]}")

    # (holes, players) → (18, N)
    return score_values


# ----- 메인 처리 함수 -----

def process_excel_file(uploaded_file, selected_holes, par_list):
    """
    업로드된 엑셀 파일을 처리:
      1) 임시 저장 → DataFrame 로드
      2) 점수 매트릭스(18 x N) 추출
      3) 신페리오 핸디캡 계산
      4) 총 타수 / 핸디캡 / 최종점수 / 랭킹 4행을 원본 뒤에 append
      5) 결과 엑셀을 임시 경로에 저장하고 경로 반환
    """
    # 1) 파일 임시 저장
    file_path = handle_uploaded_file(uploaded_file)

    # 2) 엑셀 로드 & 점수 매트릭스 추출
    df = pd.read_excel(file_path, engine="openpyxl")
    score_mat_holes_players = _extract_scores_matrix(df)  # shape (18, N)
    n_players = score_mat_holes_players.shape[1]

    # 3) 파라미터 정리
    designated_idxs = _parse_selected_holes(selected_holes)  # 길이 12, 0-index
    par = par_list

    # 플레이어별 18홀 리스트로 변환 (scores_by_player)
    # 현재 시트 구조가 "par 대비 스코어(±)" 라는 가정 유지
    scores_by_player = score_mat_holes_players.T.tolist()  # (N, 18)

    # 신페리오 핸디캡 계산 (NaN 있으면 "")
    handicap = calculate_sneperio(scores_by_player, par, designated_idxs)  # 길이 N

    # 총 타수(원 코드 의미 유지: 각 홀에서 (score + par)을 합산)
    total_strokes_vals: List[object] = []
    for j in range(n_players):
        col = score_mat_holes_players[:, j]
        # (score + par) 합계 (NaN은 0으로 볼지 무시할지 정책 선택)
        # 기존 코드와 최대한 동일하게: NaN이 섞이면 합도 NaN → 최종행에서 빈칸 처리
        if np.isnan(col).any():
            total_strokes_vals.append("")
        else:
            s = float(np.sum(col + par))
            total_strokes_vals.append(s)

    # 신페리오 최종 점수 = 총 타수 - 신페리오 핸디캡
    # (둘 중 하나라도 "" 이면 결과 "")
    handi_score_vals: List[object] = []
    for ts, h in zip(total_strokes_vals, handicap):
        if ts == "" or h == "":
            handi_score_vals.append("")
        else:
            handi_score_vals.append(round(float(ts) - float(h), 1))

    # 랭킹: 숫자만 랭킹, 빈칸은 빈칸
    ranks: List[object] = []
    numeric_idx = [i for i, v in enumerate(handi_score_vals) if isinstance(v, (int, float))]
    if numeric_idx:
        num_series = pd.Series([handi_score_vals[i] for i in numeric_idx])
        r = num_series.rank(method="min").astype(int).tolist()
        # 원 위치에 채우기
        ranks = [""] * n_players
        for k, i in enumerate(numeric_idx):
            ranks[i] = r[k]
    else:
        ranks = [""] * n_players

    # 라벨 포함 행 생성 (모두 길이 1 + n_players 보장)
    row_total     = ["총 타수"] + total_strokes_vals
    row_handicap  = ["신페리오 핸디캡"] + handicap
    row_final     = ["신페리오 핸디캡 최종 점수"] + handi_score_vals
    row_rank      = ["랭킹"] + ranks

    # 4) 원본 뒤에 4행 append (기존 마지막 행을 절대 덮어쓰지 않음)
    base = len(df)  # 기존 마지막 다음 인덱스
    for _ in range(4):
        df.loc[len(df)] = [None] * df.shape[1]

    # 쓰기: 좌측부터 필요한 개수만
    df.iloc[base + 0, 0 : 1 + n_players] = row_total
    df.iloc[base + 1, 0 : 1 + n_players] = row_handicap
    df.iloc[base + 2, 0 : 1 + n_players] = row_final
    df.iloc[base + 3, 0 : 1 + n_players] = row_rank

    # 5) 결과 저장
    out_name = f"new_perio_handicap_result_{uuid.uuid4().hex[:8]}.xlsx"
    output_path = os.path.join(tempfile.gettempdir(), out_name)
    df.to_excel(output_path, index=False)

    return output_path

