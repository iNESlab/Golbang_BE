import tempfile
import pandas as pd
import os
import requests
from django.conf import settings

from utils.tempfile_helpers import handle_uploaded_file


def process_excel_file(uploaded_file, selected_holes):
    """
    업로드된 엑셀 파일을 처리하는 함수.
    1. 파일을 임시 파일로 저장한다.
    2. 파일을 읽어 DataFrame으로 변환 후, 필요한 데이터(score)를 추출한다.
    3. GPT API를 호출하여 신페리오 계산 코드를 받아온다.
    4. exec로 코드를 실행해, 'handicap' 변수를 획득한다.
    5. DataFrame에 계산 결과(handicap), 핸디캡 스코어, 랭킹을 삽입한 후, 최종 엑셀 파일을 저장한다.
    6. 최종 파일 경로를 반환한다.
    """
    print(f"selected_holes: {selected_holes}")
    # 1. 업로드된 파일을 임시 파일로 저장
    file_path = handle_uploaded_file(uploaded_file)

    # 2. 엑셀 파일 로드 및 데이터 추출
    df = pd.read_excel(file_path)
    data = df.values.tolist()
    # 사용자 코드에서는 행 번호를 기존 행수+2로 설정함
    row = len(data) + 2

    # 홀 점수 정보만 가져옴
    score_list = [i for i in data if 'hole' in str(i[0])]
    score = [list(x) for x in zip(*[r[1:] for r in score_list])]

    # par정보
    par = [4, 4, 5, 3, 4, 3, 4, 4, 5, 4, 4, 4, 3, 4, 5, 3, 4, 5]

    # 3. GPT API 호출 함수
    api_key = settings.OPENAI_API_KEY
    if not api_key:
        raise ValueError("OPENAI_API_KEY 환경 변수가 설정되어 있지 않습니다.")

    def gpt_execute(data, par):
        url = "https://api.openai.com/v1/chat/completions"
        header = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        request_payload = {
            "model": "gpt-4o-mini",
            "messages": [
                {
                    "role": "system",
                    "content": "당신은 신페리오 계산 코드를 짜는 파이썬 프로그래머입니다"
                },
                {
                    "role": "user",
                    "content": (
                        "골프 점수를 담은 이중 리스트의 데이터가 주어지면, 이 데이터를 토대로 신페리오 핸디캡을 계산하는 파이썬 코드를 작성해주세요."
                        "입력으로 사용되는 이중 리스트 내부의 리스트 하나는 한 사람의 1~18홀에 대한 골프 점수를 순서대로 나타냅니다."
                        "코드는 반환되면 검토를 거치지 않고 바로 사용할 수 있도록 되도록이면 간단하고 직관적이게 짜주세요."
                        "신페리오 핸디캡 계산 수식은 다음과 같습니다. 신페리오 핸디캡 = (((선택된 12개 hole의 score + 각 hole의 par값) × 1.5) - 72) × 0.8"
                        "이때 선택되는 hole의 번호는 모든 사용자에게 같아야 하고, par정보는 고정된 값으로 주어집니다. "
                        "해당 코드의 반환 형태는 계산된 신페리오 값을 순서대로 넣은 리스트 형태면 됩니다. 이때 Nan 값을 갖는 리스트들의 반환 값은 빈 문자열 처리 해주세요."
                        "예시 입력: [[1.0, 0.0, 1.0, 2.0, 0.0, 0.0, 1.0, 1.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 1.0, 2.0, 2.0], [nan, nan, nan, nan, nan, nan, nan, nan, nan, nan, nan, nan, nan, nan, nan, nan, nan, nan]]"
                        "예시 출력: [-49.2,""]"
                        "위의 입출력 형태를 만족할 수 있도록 코드를 짜주세요. 또한 최종 출력은 handicap이라는 변수 안에 담기도록 코드를 짜주세요."
                        "결과 이외의 추가적인 설명은 절대 포함하지 말고, 데이터를 변형시키지 마세요."
                        f"골프 score 데이터는 여기 있습니다: {data}"
                        f"골프 par 데이터는 여기 있습니다: {par}"
                        f"사용자가 선택한 홀 번호는 여기 있습니다.: {selected_holes} (홀은 1~18 홀 사이로 전달해주고 있으니 0-index 처리를 하지 마세요.)"
                    )
                }
            ]
        }
        response = requests.post(url, headers=header, json=request_payload)

        if response.status_code == 200:
            raw_content = response.json()["choices"][0]["message"]["content"]
            raw_content = raw_content.strip()
            if raw_content.startswith("```python"):
                raw_content = raw_content[9:]
            if raw_content.endswith("```"):
                raw_content = raw_content[:-3]
        else:
            raise Exception(f"OpenAI API 오류: {response.status_code}")
        return raw_content

    # 4. GPT API 호출 및 코드 실행
    result = gpt_execute(score, par)
    print(result)

    exec_env = {}
    exec(result, exec_env)

    # 5. DataFrame에 계산 결과(handicap), 핸디캡 스코어, 랭킹을 삽입
    handicap = exec_env.get("handicap")
    handicap.insert(0, '신페리오 핸디캡')

    total_score = next(i for i in data if '전체 스코어' in str(i[0]))
    handi_score = [total_score[i] - handicap[i] for i in range(1, len(total_score))]
    handi_score.insert(0, '신페리오 핸디캡 스코어')

    rank = pd.Series(handi_score[1:]).rank(method='min').astype(int).tolist()
    rank.insert(0, '랭킹')

    while row >= df.shape[0]:
        df.loc[df.shape[0]] = [None] * df.shape[1]

    df.iloc[row - 2, 0:len(handicap) + 1] = handicap
    df.iloc[row - 1, 0:len(handicap) + 1] = handi_score
    df.iloc[row, 0:len(handicap) + 1] = rank

    # 6. 최종 엑셀 파일 저장
    output_path = os.path.join(tempfile.gettempdir(), "new_perio_handicap_result.xlsx")
    df.to_excel(output_path, index=False)

    return output_path
