import tempfile


def handle_uploaded_file(uploaded_file):
    """
    임시 파일에 저장하고, 경로를 반환하는 함수

    :param uploaded_file: 임시 파일로 저장할 파일
    :return: 임시 저장한 파일의 경로
    """

    # 파일 확장자 검증. 엑셀 파일만 가능
    if not uploaded_file.name.endswith('.xlsx'):
        raise ValueError("엑셀 파일만 업로드할 수 있습니다.")

    # 파일 크기 제한: 최대 10MB (10 * 1024 * 1024 bytes) (보통 10KB 이하)
    if uploaded_file.size > 10 * 1024 * 1024:
        raise ValueError("파일 크기가 너무 큽니다. 최대 10MB까지 허용됩니다.")

    # 임시 파일 저장
    with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp:
        for chunk in uploaded_file.chunks():
            tmp.write(chunk)
        return tmp.name