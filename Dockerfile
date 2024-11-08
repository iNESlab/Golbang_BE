# 베이스 이미지 설정
FROM python:3.12.4-slim
LABEL authors="minjeong"

# 작업 디렉토리 설정
WORKDIR /app

# 필요 패키지 설치
RUN apt-get update && apt-get install -y \
    build-essential \
    pkg-config \
    libmariadb-dev \
    qt5-qmake \
    qtbase5-dev \
    && apt-get clean

# 필요 패키지 복사 및 설치
COPY requirements.txt .
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# wait-for-it.sh 스크립트 복사
COPY wait-for-it.sh /wait-for-it.sh

# wait-for-it.sh 실행 권한 부여
RUN chmod +x /wait-for-it.sh

# 프로젝트 파일 복사
COPY . .

# 환경 변수 설정
ENV DJANGO_SETTINGS_MODULE=golbang.settings

# 포트 설정
EXPOSE 8000

# 명령어 설정
CMD ["/wait-for-it.sh", "db:3306", "--", "/wait-for-it.sh", "redis:6379", "--", "sh", "-c", "\
    python manage.py makemigrations && \
    python manage.py migrate && \
    python create-superuser.py && \
    python manage.py runserver 0.0.0.0:8000"]
