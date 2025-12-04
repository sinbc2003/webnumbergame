## 숫자게임 웹 백엔드

FastAPI + SQLModel 기반의 실시간 숫자게임 플랫폼 백엔드입니다.

### 주요 기능
- JWT 인증 및 회원 가입/로그인
- 방 생성/참가, 1라운드 개인전 · 2라운드 팀전 라운드 제어
- 16강 토너먼트 편성 및 시드 배치 API
- 실시간 웹소켓 이벤트(방/대시보드)1123
- 대시보드 통계 및 랭킹 집계

### 개발 환경
```bash
cd backend
poetry install
poetry run uvicorn app.main:app --reload
```

환경 변수(.env)
```
DATABASE_URL=postgresql+asyncpg://USER:PASSWORD@HOST:PORT/DB
SECRET_KEY=랜덤문자열
NEXT_PUBLIC_API_BASE=http://localhost:8000/api
CORS_ORIGINS=["http://localhost:3000","https://number-game-web-170807697050.asia-northeast3.run.app"]
DB_INIT_MAX_RETRIES=5
DB_INIT_RETRY_INTERVAL_SECONDS=2
``` 

### 관리자 엔드포인트
- `/api/admin/problems` (GET/POST/PUT/DELETE): 라운드별 문제 데이터 CRUD
- `/api/admin/reset` (POST): 방/매치/토너먼트 등 테스트 데이터를 일괄 삭제
- 모든 엔드포인트는 `is_admin=True` 인 사용자에게만 허용됩니다.

Cloud Run 배포 시 `poetry export`로 requirements.txt를 생성하거나 Dockerfile에서 직접 poetry를 사용하면 됩니다.  11 