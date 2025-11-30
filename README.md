# 숫자게임 웹 플랫폼

FastAPI 백엔드와 Next.js 프론트엔드로 구현한 실시간 숫자게임 토너먼트 서비스입니다. 기존 `참고/` 폴더의 `NumberGame.exe` 로직을 웹으로 포팅하여 1라운드 개인전 / 2라운드 팀전, 16강 토너먼트, 실시간 대시보드/랭킹을 지원합니다.

## 모노레포 구조

```
backend/   # FastAPI + SQLModel + WebSocket
frontend/  # Next.js 14(App Router) + Tailwind
참고/        # 기존 데스크톱 버전 참고 자료
```

## 로컬 개발

### 1) 백엔드
```bash
cd backend
python -m venv .venv
.venv\Scripts\activate  # Windows
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

필수 환경 변수(.env)
```
DATABASE_URL=sqlite+aiosqlite:///./number_game.db   # 또는 Cloud SQL/Postgres URL
SECRET_KEY=랜덤문자열
```

### 2) 프론트엔드
```bash
cd frontend
npm install
npm run dev -- --port 3000
```

`.env.local`
```
NEXT_PUBLIC_API_BASE=http://localhost:8000/api
NEXT_PUBLIC_WS_BASE=ws://localhost:8000
```

## 핵심 기능 요약
- 회원가입/로그인(JWT) 및 사용자 레이팅/전적 관리
- 방 생성·참가, 3분 라운드 타이머, WebSocket 실시간 이벤트
- 숫자식 파서/코스트 계산(기존 exe 의 `calculator.py` 이식)
- 16강 토너먼트 시드 배정/브래킷 API 및 대회 화면
- 대시보드 요약/랭킹 + 실시간 접속자 스트림

## GCP Cloud Run 배포 가이드

### 1) Cloud SQL(Optional)
1. PostgreSQL 인스턴스 생성
2. DB/사용자 생성 후 `DATABASE_URL=postgresql+asyncpg://USER:PASSWORD@HOST:PORT/DB` 형태로 구성
3. Cloud Run 서비스에 해당 값을 시크릿/환경 변수로 주입

### 2) 백엔드 컨테이너
```bash
cd backend
gcloud builds submit --tag gcr.io/PROJECT_ID/number-game-api
gcloud run deploy number-game-api \
  --image gcr.io/PROJECT_ID/number-game-api \
  --region asia-northeast3 \
  --port 8000 \
  --set-env-vars SECRET_KEY=...,DATABASE_URL=... \
  --allow-unauthenticated
```

### 3) 프론트엔드 컨테이너
```bash
cd frontend
gcloud builds submit --tag gcr.io/PROJECT_ID/number-game-web
gcloud run deploy number-game-web \
  --image gcr.io/PROJECT_ID/number-game-web \
  --region asia-northeast3 \
  --port 3000 \
  --set-env-vars NEXT_PUBLIC_API_BASE=https://number-game-api-xxxx.a.run.app/api,\
                 NEXT_PUBLIC_WS_BASE=wss://number-game-api-xxxx.a.run.app \
  --allow-unauthenticated
```

### 4) GitHub Actions 연동 아이디어
1. GitHub Secrets에 `GCP_PROJECT`, `GCP_SA_KEY`, `API_SERVICE`, `WEB_SERVICE` 설정
2. 백엔드/프론트엔드 각각 `cloud-run.yml` 워크플로를 만들어 `git push` 시 자동 빌드/배포

## 숫자게임 규칙 반영
- `backend/app/game/calculator.py`: 1, +, *, () 조합만 허용하도록 입력 전처리
- `backend/app/game/engine.py`: 목표값 대비 거리, 최적 코스트와의 차이, 남은 시간으로 점수 계산
- `backend/app/services/game_service.py`: 제출 시 승부 판정 및 기록/랭킹 반영

## 다음 단계 제안
- Redis Pub/Sub 도입으로 멀티 인스턴스에서도 WebSocket 상태 공유
- Cloud Scheduler + Pub/Sub으로 토너먼트 자동 라운드 전환
- 관리자 UI(문제/코스트 편집) 추가
- 관전자 뷰/실시간 스트리밍 강화

> ⚠️ 배포 전 `NEXT_PUBLIC_API_BASE`, `NEXT_PUBLIC_WS_BASE` 값을 실제 Cloud Run URL로 교체한 뒤 `git add` / `git commit` / `git push` / `gcloud run deploy` 절차를 사용자 요청에 따라 수동으로 실행하세요.

