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
```

Cloud Run 배포 시 `poetry export`로 requirements.txt를 생성하거나 Dockerfile에서 직접 poetry를 사용하면 됩니다.  

1  11 

