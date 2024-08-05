## v0.1.0 (2024-08-01)

### Feat

- pre-commit, commitizen 재테스트

## v0.2.0 (2024-08-01)

### Feat

- pre-commit, conventional commit 테스트
- Github Actions CI/CD workflow 추가.yml
- Dockerfile과 docker-compose 등 기타 필요한 파일 추가
- events post api 생성
- participants 기본 crud 생성
- clubMembers 기본 crud 생성
- Open API 문서UI tool(Swagger&Redoc)과 연결하여 API 문서 생성
- 토큰 관련 예외처리 추가
- flutter와 연결하기 위해 CORS 패키지 연결
- 새로운 골방 프로젝트 생성

### Fix

- **cz.toml**: cz.toml의 tag_format이 동적으로 바뀔 수 있도록 중괄호 대신 $로 변경
- 데이터베이스 초기화 및 마이그레이션 문제 해결
- docker-compose run을 사용하도록 GitHub 작업 워크플로 업데이트
- swap 공간 추가 및 마이그레이션 문제 해결
- 마이그레이션 충돌 해결 및 GitHub 작업 워크플로 업데이트
- mysql 클라이언트 경로 수정
- 마이그레이션을 실행하기 전에 데이터베이스 삭제 및 다시 만들기
- KAKAO_CALLBACK_URL을  GitHub Actions workflow에 추가
- "Run tests" step 에러를 해결하기 위해  ci-cd.yml 수정
- ci-cd.yml 내의 mariadb 오타 수정
- ci-cd.yml 내 syntax 에러 수정
- 전체 코드 초기화