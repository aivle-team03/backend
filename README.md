# 🛡️ AI 기반 산업/소방 안전 모니터링 백엔드 API 시스템

![FastAPI](https://img.shields.io/badge/FastAPI-005571?style=for-the-badge&logo=fastapi)
![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)
![MySQL](https://img.shields.io/badge/MySQL-4479A1?style=for-the-badge&logo=mysql&logoColor=white)
![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-D71F00?style=for-the-badge&logo=sqlalchemy&logoColor=white)
![JWT](https://img.shields.io/badge/JWT-black?style=for-the-badge&logo=JSON%20web%20tokens)
![Pydantic](https://img.shields.io/badge/Pydantic-E92063?style=for-the-badge&logo=pydantic&logoColor=white)

> **AIVLE Team 03 백엔드 서비스**  
> 사업장 내 이상 상황(화재, 적치물, 보호구 미착용 등)을 실시간 모니터링하고, 현장 조치 체크리스트 전이 관리, 정기 점검 이력 자동 스케줄링, 구역별 안전 위험도 연산, 소방 법규/매뉴얼 챗봇, AI 비전 감지 및 조치 검증, 안전 교육 & AI 영상 생성 파이프라인, 보고서 PDF 생성까지 통합 제공하는 RESTful 백엔드 API 서버입니다.

---

## 📌 주요 기능 (Key Features)

### 🔑 1. 인증/인가 및 권한별 사용자 관리 (`/api/auth`, `/api/users`, `/api/admin`)
- **JWT 토큰 인증**: Access/Refresh 토큰 기반 사용자 인증 및 비밀번호 Bcrypt 암호화
- **회원가입 & 초대 코드**: 안전관리자 전용 회원가입 고유 초대 코드 생성 및 유효성 검증 (`/api/auth/verify-code`)
- **역할 및 카테고리 관리**: 역할(안전관리자, 관제사, 현장관리자, 일반유저) 및 장비 카테고리(지게차, 화물트럭, 토잉카 등) 지정/수정 (`/api/admin/users/{uid}`)
- **마이페이지 & 계정 관리**: 내 정보 조회, 비밀번호 변경 (`/api/users/me/password`), 알림 설정 ON/OFF (`/api/users/me/notifications`), 비밀번호 찾기

### 📹 2. CCTV 모니터링 관리 (`/api/cctvs`)
- 구역별 CCTV 대수, 실시간 스트리밍 URL, 위치, 작동 상태(정상/비정상) CRUD 관리

### 🚨 3. 이상 상황 모니터링 및 현장 조치 요청 (`/api/monitoring`)
- 실시간 이상 감지 이벤트 발생 이력 조회 및 모니터링
- 관리자가 이상 이벤트 발견 시 현장 조치 담당자 지정 및 메시지 할당 ➡️ `Checklist` 조치 레코드 자동 생성

### 📋 4. 체크리스트 & 현장 조치 생명주기 관리 (`/api/checklists`)
- **상태 흐름**: `조치 필요/대기` ➡️ `조치 중` ➡️ `승인 대기` ➡️ `승인 완료` (또는 `반려`)
- **조치 담당자 연동**: 조치 담당자 검색 (`/api/checklists/managers`) 및 담당자 배정 (`/api/checklists/{id}/assign`)
- **현장 조치 보고**: 작업자의 조치 사진/설명 업로드 (`multipart/form-data`) 및 관리자 검토/승인 워크플로우
- **이력 및 내 조치**: 조치 완료/이력 조회 및 로그인된 사용자의 담당 체크리스트 목록 제공 (`/api/checklists/me`)

### 🔍 5. 정기 점검 항목 및 이력 스케줄링 관리 (`/api/inspection`)
- **점검 항목 Master CRUD**: 매일/매주/매월 정기 점검 항목 생성, 수정, 삭제, 상세 조회 (`/api/inspection`)
- **점검 수행 이력 생성 및 조회**: 전체 이력(`all`), 내 배정 이력(`me`), 단건 상세 조회
- **자동 스케줄링 배치 파이프라인**: `APScheduler` 기반으로 매일 자정(00시 00분) 오늘 자 정기 점검 이력을 자동 분산 생성 (`run_daily_inspection_job`)
- **수동 스케줄링 트리거**: 즉시 오늘 자 정기 점검 이력을 수동으로 갱신하는 API 지원 (`POST /api/inspection/histories/trigger-scheduled`)

### 🛠️ 6. 조치 이력 관리 (`/api/action-histories`)
- 안전 제보 게시글, 이상 감지 이벤트, 점검 수행 이력 기반 현장 조치 프로세스 일관성 관리
- 조치 상태 변경(`조치 필요` ➡️ `조치 완료`), 담당자/승인자 지정 및 조치 내용/사진 첨부

### ⚠️ 7. 위험요인 & 매트릭스 관리 (`/api/risk`)
- 위험요인 (Event Category) 목록 조회 (`/api/risk/list`)
- 카테고리별 위험 강도(1~10 Level) 수정 및 신규 위험요인 카테고리 추가/삭제

### 📄 8. 안전 보고서 관리 & PDF 다운로드 (`/api/report`)
- 이상 감지 이벤트 및 조치 체크리스트 항목을 선택하여 자동 보고서 생성 (`POST /api/report`)
- 보고서 목록/상세 조회, 수정, 삭제
- **PDF 동적 다운로드**: 보고서 상세 내용을 표준 PDF 문서 형태로 다운로드 서빙 (`GET /api/report/{id}/download`)

### 📊 9. 대시보드 통계 & 종합 안전 등급 (`/api/dashboard`)
- **구역별 실시간 위험 지수**: CCTV 위치 단위 미해결 이벤트 비율 기반 위험도 연산 (0~100점)
- **종합 안전 등급 계산**: 최근 30일 이내 감지 이벤트의 미해결 상태별 감점 수식 적용 ➡️ **A ~ F 등급** 자동 산출 및 원인 분석 요약
- 기간별 통계 리포트 조회 및 AI 분석 보고서 요약 텍스트 제공

### 🎓 10. 안전 교육 관리 & AI 영상 제작 파이프라인 (`/api/education`, `/api/admin/education`)
- **유저 수강 관리**: 개인별 마감/진행/완료 교육 요약, 교육 목록 조회, 필수/정기 교육 이수율(%) 연산 및 80% 이상 수강 시 완료 처리 (`/api/education/{id}/complete`)
- **관리자 대시보드 및 수강 대상자 목록**: 관리자 교육 대시보드 요약 (`/api/admin/education/dashboard`), 카테고리별 이수 통계 (`/api/admin/education/category-stats`), 교육별 수강 대상자 목록 조회 (`/api/admin/education/{id}/attendees`)
- **AI 교육 영상 제작 (영상 생성 서비스 연동)**: 문서(PDF/PPTX/TXT) 또는 텍스트 입력을 받아 영상을 자동 제작합니다 (`/api/education/veo-generate`). 실제 생성은 별도 서비스인 **[aivle-team03/AI](https://github.com/aivle-team03/AI) 의 `videoagent`** 가 담당하며, 이 백엔드는 다음만 책임집니다.
  - **인증 및 테넌시**: 관리자 인증, `company_id` 판별 후 생성 서비스로 전달 (클라이언트 입력을 신뢰하지 않음)
  - **결과 영속화**: 프론트가 `status` API를 폴링하는 동안 작업이 완료되면 `Education` 테이블에 적재 (`video_url` 기준 멱등 처리로 중복 방지)
  - **소유권 검증**: 다른 회사의 `task_id` 조회 차단
  - 업로드 문서는 디스크에 저장하지 않고 메모리를 통해 그대로 전달합니다.

### 📌 11. 공지사항 & 안전 게시판 (`/api/boards`)
- 사내 공지 및 안전 제보/커뮤니티 게시판 CRUD
- 키워드, 카테고리, 위치, 조치 상태별 게시글 검색 및 현장 사진 파일 첨부 업로드 기능 제공

### 🤖 12. 소방안전 챗봇 & 법규/매뉴얼 검색 (`/api/chatbot`, `/api/data`)
- 소방/안전 키워드 기반 자연어 질의응답 매칭 엔진
- 초기 추천 질문 목록(4종) 제공
- 소방시설법, 산업안전보건법 및 사내 소방 매뉴얼 키워드 검색 지원

### 🧠 13. AI 비전 탐지 & 조치 결과 검증 (`/api/ai`)
- **소방시설 탐지**: 이미지 내 소화기 등의 바운딩 박스(`bbox`) 및 신뢰도 탐지
- **위험요소 탐지**: 비상구 통로 불법 적치물/장애물 검지 및 위험 수준(`High`/`Low`) 판정
- **화재 징후 탐지**: CCTV 프레임 내 농연(Smoke) 및 불꽃 징후 감지 및 비상 경보 메시지 리턴
- **조치결과 재확인**: 조치 전/후 사진 2장을 수신하여 시각적 유사도 분석 및 위험 요소 해결 여부 AI 검증

### ⚙️ 14. 글로벌 예외 처리 & 파일 로깅 & CORS
- 서버 전역 예외(`HTTPException`, `RequestValidationError`, `Exception`)를 통일된 JSON 구조로 가공하여 전달
- `RotatingFileHandler` 기반 `logs/app.log` 로그 자동 적재 및 관리 (5MB, 백업 파일 최대 5개 회전)
- 프론트엔드 연동을 위한 전역 **CORS 미들웨어** 탑재 및 정적 파일 서빙 (`/static`)

---

## 🛠 기술 스택 (Tech Stack)

| 구분 | 기술 / 라이브러리 |
| :--- | :--- |
| **Language** | Python 3.14 (개발 환경 기준) |
| **Framework** | FastAPI |
| **Database & ORM** | MySQL, SQLAlchemy, PyMySQL |
| **Auth & Security** | python-jose (JWT), Passlib (Bcrypt), Python-Multipart |
| **Validation & Serialization** | Pydantic v2 |
| **External Service** | httpx (영상 생성 서비스 videoagent 연동) |
| **Scheduler** | APScheduler (BackgroundScheduler) |
| **Media & Storage** | boto3 (AWS S3) |
| **Server Engine** | Uvicorn, WatchFiles |
| **File Processing & PDF** | ReportLab (PDF Generation) |
| **Container** | Docker, Docker Compose |

---

## 📂 프로젝트 구조 (Directory Structure)

```text
backend/
├── app/
│   ├── api/
│   │   ├── endpoints/        # API 라우터 컨트롤러 (auth, user, cctv, monitoring, checklist, inspection, action_history, risk, report, dashboard, education, board, chatbot, ai_detect)
│   │   └── routers.py        # 통합 API 라우터 매핑
│   ├── core/                 # 암호화(crypt), 전역 예외/로깅(exceptions)
│   ├── crud/                 # DB 비즈니스 로직 / CRUD 모듈 (inspection, action_history, education 등)
│   ├── db/                   # DB 연결 세션 및 Base 선언 (db.py)
│   ├── models/               # SQLAlchemy ORM 모델 (User, CCTV, Event, Checklist, Inspection, ActionHistory, Report, Board, Education 등)
│   ├── schemas/              # Pydantic DTO 데이터 스키마
│   ├── services/             # (영상 생성 로직은 AI 저장소로 이관됨)
│   ├── utils/                # S3, 날짜(KST), 인증 유틸
│   └── main.py               # FastAPI 애플리케이션 엔트리포인트 (APScheduler 탑재)
├── logs/                     # 서버 런타임 회전 파일 로그 (app.log)
├── static/
│   └── uploads/              # 현장 조치 및 게시판 업로드 이미지 서빙 디렉토리
├── tests/                    # 테스트 코드
├── seed.py                   # DB 자동 시딩 스크립트 (더미 데이터 일괄 적재)
├── Dockerfile                # 애플리케이션 컨테이너 이미지
├── docker-compose.yml        # web 컨테이너 기동
├── CLAUDE.md                 # AI 코딩 어시스턴트 작업 가이드라인
├── .env                      # 환경 변수 설정
├── requirements.txt          # 파이썬 의존성 패키지
└── README.md
```

---

## 🚀 시작하기 (Quick Start)

### 1. 가상환경 생성 및 패키지 설치

```bash
# 가상환경 생성
python -m venv .venv

# 가상환경 활성화 (Windows)
.venv\Scripts\activate

# 가상환경 활성화 (Mac/Linux)
source .venv/bin/activate

# 의존성 패키지 설치
pip install -r requirements.txt
```

### 2. 환경 변수 (`.env`) 설정

프로젝트 루트에 `.env` 파일을 생성하고 데이터베이스 및 보안 정보를 설정합니다.

```env
# --- 필수: DB & 인증 ---
DATABASE_URL="mysql+pymysql://<DB_USER>:<DB_PASSWORD>@<DB_HOST>:3306/<DB_NAME>"
SECRET_KEY="your-secret-key"
ALGORITHM="HS256"
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# --- 필수: 영상 생성 서비스 ---
VIDEO_AGENT_URL="http://127.0.0.1:8100"
# Redis는 VideoAgent 완료 확인과 자동 DB 등록을 수행하는 Celery 워커가 사용한다.
REDIS_URL="redis://127.0.0.1:6379/0"

# --- 선택 ---
ENV="development"                        # "production" 이면 DATABASE_URL / SECRET_KEY 미설정 시 기동 거부
AWS_ACCESS_KEY_ID=""
AWS_SECRET_ACCESS_KEY=""
AWS_REGION=""
BACKEND_URL=""
```

# REPORT AWS 설정
'''
AWS_REPORT_ACCESS_KEY_ID=""
AWS_REPORT_SECRET_ACCESS_KEY=""
AWS_REPORT_REGION=us-east-1
AWS_REPORT_S3_BUCKET_NAME=aivle-team3-boss-bucket

'''

> `ENV`를 `production`으로 설정하면 `DATABASE_URL`과 `SECRET_KEY`가 없을 때 예외를 던지며 기동을 거부합니다. 미설정 시에는 각각 로컬 SQLite와 개발용 기본 키로 폴백하므로, **운영 배포 시 `ENV=production` 지정을 권장합니다.**

### 3. 데이터베이스 초기 시딩 (Optional)

개발 및 테스트용 모의 데이터(유저, CCTV, 이상 이벤트, 체크리스트, 리포트, 교육, 게시글 등)를 일괄 적재합니다.

```bash
python seed.py
```

### 4. 서버 기동

영상 생성 서비스(`videoagent`)와 Redis가 별도로 떠 있어야 AI 영상 생성 기능이 동작합니다.
API 서버와 Celery 워커를 각각 기동하세요.

```bash
uvicorn app.main:app --reload
# 별도 터미널
celery -A app.celery_app.celery_app worker --pool=solo --concurrency=1 --loglevel=INFO --queues=video_generation
```

또는 Docker로:

```bash
docker compose up --build
```

> 영상 생성 서비스 기동 방법은 [aivle-team03/AI](https://github.com/aivle-team03/AI) 의 `videoagent/README.md` 를 참고하세요.
> 그 서비스가 떠 있지 않으면 `/api/education/veo-generate` 요청이 `502`를 반환합니다.

- **API 서버 주소**: `http://127.0.0.1:8000`
- **Swagger API 문서**: `http://127.0.0.1:8000/docs`
- **ReDoc API 문서**: `http://127.0.0.1:8000/redoc`

### 5. AI 영상 생성 사용 흐름

```bash
# 1) 생성 요청 → task_id 수신 (202 Accepted)
#    due_date, title/category/type은 백엔드 작업 레코드에 저장된다.
POST /api/education/veo-generate   (multipart: file 또는 text_content, due_date)

# 2) 진행 상태 폴링 (progress_percent 0 → 100)
GET  /api/education/veo-generate/{task_id}/status

# 3) Celery 워커가 완료를 확인한 뒤 Education 테이블에 자동 적재
#    quality_report.hitl_required=true 이면 자동 게시하지 않고 검토 대기로 남긴다.
```

영상 생성은 API 서버와 별도로 Celery 워커가 필요합니다. Redis와 VideoAgent가 실행 중인
환경에서 다음 명령으로 워커를 실행하세요.

```bash
celery -A app.celery_app.celery_app worker --pool=solo --concurrency=1 --loglevel=INFO --queues=video_generation
```

작업 상태는 영상 생성 서비스가 **24시간** 보관합니다. 완료 시 백엔드가 `Education` 테이블에 적재하며, 이후에는 일반 교육 목록 API로 조회합니다.

---

## 📋 API 엔드포인트 명세 요약 (API Reference)

| Category | Method | Endpoint | Description |
| :--- | :---: | :--- | :--- |
| **Auth** | `POST` | `/api/auth/signup` | 신규 회원가입 |
| | `GET` | `/api/auth/verify-code` | 회원가입 코드 유효성 검증 |
| | `GET` | `/api/auth/checkid` | 사용자 아이디 중복 확인 |
| | `POST` | `/api/auth/login` | 로그인 및 JWT Access Token 발급 |
| | `POST` | `/api/auth/logout` | 로그아웃 (토큰 무효화) |
| | `POST` | `/api/auth/find/password` | 비밀번호 찾기/재설정 |
| | `POST` | `/api/auth/refresh` | Access Token 재발급 |
| **Users** | `GET` | `/api/users/me` | 로그인 사용자 내 정보 조회 |
| | `PATCH` | `/api/users/me/password` | 내 비밀번호 변경 |
| | `DELETE ` | `/api/users/me` | 회원 탈퇴 |
| **Admin** | `GET` | `/api/admin/categories` | 유저 카테고리 목록 조회 |
| | `POST` | `/api/admin/invite-codes` | 가입 회원가입 초대 코드 생성 |
| | `GET` | `/api/admin/invite-codes` | 발급된 회원가입 초대 코드 목록 조회 |
| | `GET` | `/api/admin/users` | 관리자용 전체 유저 목록 조회 |
| | `PATCH` | `/api/admin/users/{uid}` | 유저 역할 및 장비 카테고리 수정 |
| | `PATCH` | `/api/admin/{uid}/role` | 유저 역할 변경 |
| **CCTV** | `GET` | `/api/cctvs` | CCTV 목록 및 상태 조회 |
| | `POST` | `/api/cctvs` | 신규 CCTV 등록 |
| | `GET` | `/api/cctvs/{camera_id}` | 특정 CCTV 상세 조회 |
| | `DELETE` | `/api/cctvs/{camera_id}` | 특정 CCTV 삭제 |
| **Monitoring** | `GET` | `/api/monitoring/events` | 이상 감지 이벤트 목록 조회 |
| | `GET` | `/api/monitoring/events/{event_id}` | 특정 이상 감지 이벤트 조회 |
| | `POST` | `/api/monitoring/events/{event_id}/request` | 현장 조치 요청 (체크리스트 생성) |
| **Inspection** | `GET` | `/api/inspection` | 회사의 점검 항목 목록 조회 |
| | `POST` | `/api/inspection` | 신규 점검 항목 등록 |
| | `GET` | `/api/inspection/{id}` | 특정 점검 항목 상세 조회 |
| | `PATCH` | `/api/inspection/{id}` | 점검 항목 정보 수정 |
| | `DELETE`| `/api/inspection/{id}` | 점검 항목 삭제 |
| | `GET` | `/api/inspection//{id}/histories` | 특정 점검 항목의 전체 이력 목록 조회 |
| | `GET` | `/api/inspection/histories/all` | 회사 전체 점검 이력 목록 조회 |
| | `GET` | `/api/inspection/histories/me` | 내게 배정된 점검 이력 목록 조회 |
| | `GET` | `/api/inspection/histories/{id}` | 점검 이력 단건 상세 조회 |
| | `POST` | `/api/inspection/histories/create` | 점검 수행 이력 신규 생성 |
| | `PATCH` | `/api/inspection/histories/{id}` | 점검 수행 이력 상태/내용 수정 |
| | `DELETE`| `/api/inspection/histories/{id}` | 점검 수행 이력 삭제 |
| | `POST` | `/api/inspection/histories/trigger-scheduled` | 스케줄링 점검 이력 수동 실행 |
| **ActionHistory** | `GET` | `/api/action-histories` | 전체 조치 이력 목록 조회 |
| | `POST` | `/api/action-histories` | 조치 이력 생성 |
| | `GET` | `/api/action-histories/handlers` | 전체 작업자 조회 |
| | `PATCH` | `/api/action-histories/assignments` | 조치 담당자 배정 |
| | `GET` | `/api/action-histories/me` | 내게 배정된 조치 이력 조회 |
| | `GET` | `/api/action-histories/{id}` | 조치 이력 상세 조회 |
| | `PATCH` | `/api/action-histories/{id}/complete` | 조치 이력 완료 |
| | `PATCH` | `/api/action-histories/{id}/approve` | 완료된 조치 이력 승인 |
| | `PATCH` | `/api/action-histories/{id}/reject` | 완료된 조치 이력 반려 |
| **Risk** | `GET` | `/api/risk/list` | 위험요인 카테고리 목록 조회 |
| | `PATCH` | `/api/risk/category/{id}/level` | 카테고리별 위험 강도(1~10) 수정 |
| | `POST` | `/api/risk/category` | 신규 위험요인 카테고리 등록 |
| | `DELETE`| `/api/risk/category/{id}` | 위험요인 카테고리 삭제 |
| **Report** | `POST` | `/api/report` | 이벤트/체크리스트 기반 안전 보고서 생성 |
| | `GET` | `/api/report` | 보고서 목록 조회 (검색/필터) |
| | `GET` | `/api/report/{id}` | 보고서 상세 조회 |
| | `PUT` | `/api/report/{id}` | 보고서 내용 수정 |
| | `DELETE`| `/api/report/{id}` | 보고서 삭제 |
| | `GET` | `/api/report/{id}/download` | 보고서 PDF 파일 동적 다운로드 |
| | `GET` | `/api/report/{report_id}/file-url` | S3 저장소 저장 파일 임시 URL 발급 |
| | `POST` | `/api/report/risk-assessment/form/generate` | 위험성평가표 생성 |
| | `POST` | `/api/report/worker-feedback/generate` | 종사자에 의한 유해 위험요인 보고서 생성 |
| | `POST` | `/api/report/management-review-order/generate` |경영책임지 검토지시서 생성 |
| | `POST` | `/api/report/risk-assessment/report/generate` | 위험성평가보고서 생성 |
| **Dashboard**| `GET` | `/api/dashboard/summary` | 감지, 위반, 조치 대기/완료 건수 요약 |
| | `GET` | `/api/dashboard/recentevents` | 최근 발생한 이상 항목 리스트 조회 |
| | `GET` | `/api/dashboard/zones/stats` | 구역별 위험도 집계 통계 |
| | `GET` | `/api/dashboard/safetygrade` | 최근 30일 기반 종합 안전 등급 (A~F) |
| | `GET` | `/api/dashboard/reports` | 기간별 통계 보고서 조회 |
| | `GET` | `/api/dashboard/reports/summary` | 보고서 AI 분석 요약 |
| **Education**| `GET` | `/api/education/list` | 내 교육 영상 조회 |
| | `GET` | `/api/education/summary` | 유저 상단 요약 건수 (마감, 진행중, 이수) |
| | `GET` | `/api/education/status` | 유저 내 교육 리스트 조회 |
| | `GET` | `/api/education/completion-rates` | 유저 필수/정기/전체 교육 이수율(%) |
| | `POST` | `/api/education/{id}/complete` | 비디오 수강 이수 완료 처리 |
| | `POST` | `/api/education/{id}/progress` | 교육 영상 시청 진척도 업데이트 |
| | `POST` | `/api/education/add` | 교육 영상 직접 추가 |
| | `GET` | `/api/admin/education/dashboard` | 관리자 교육 대시보드 종합 통계 조회 |
| | `GET` | `/api/admin/education/category-stats` | 관리자 카테고리별 이수 현황 통계 |
| | `GET` | `/api/admin/education/status` | 관리자 대상자별 교육 리스트/이수 요약 |
| | `GET` | `/api/admin/education/{id}/attendees` | 특정 교육 수강 대상자 목록 조회 |
| | `GET` | `/api/admin/education/{uid}` | 관리자 특정 유저 교육 상세 조회 |
| | `POST` | `/api/education/veo-generate` | Google Veo AI 영상 생성 비동기 요청 |
| | `GET` | `/api/education/veo-generate/pending` | 제작 중이거나 검토가 필요한 비디오 조회 |
| | `GET` | `/api/education/veo-generate/{task_id}/status` | Veo 영상 생성 진행 상태 및 품질 검수 결과 조회 |
| | `POST` | `/api/education/veo-generate/{task_id}/publish` | 검토가 완료된 영상 최종 등록 |
| | `DELETE` | `/api/education/{education_id}` | 교육 영상 삭제 |
| **Board** | `POST` | `/api/boards` | 게시글 등록 (사진 파일 첨부) |
| | `GET` | `/api/boards` | 게시글 목록 조회 (검색/필터ing) |
| | `GET` | `/api/boards/{id}` | 게시글 상세 조회 |
| | `PATCH` | `/api/boards/{id}` | 게시글 수정 |
| | `DELETE`| `/api/boards/{id}` | 게시글 삭제 |
| | `PATCH` | `/api/boards/{id}/status` | 게시글 처리 상태 변경 |
| **Chatbot** | `POST` | `/api/chatbot/query` | 안전 질의응답 챗봇 |
| | `GET` | `/api/chatbot/recommendations` | 추천 질문 목록 (4종) |
| **Data** | `GET` | `/api/data/manuals` | 소방법/산업안전 매뉴얼 검색 |
| **AI Detect** | `POST` | `/api/ai/detect/events` | 이상 감지 시 이벤트 추가 |
| | `POST` | `/api/ai/detect/verify-action` | 조치결과 재확인 |
| **Notification** | `GET` | `/api/notifications/` | 전체 알림 조회 |
| | `PATCH` | `/api/notifications/read-all` | 전체 알림 읽음 처리 |
| | `PATCH` | `/api/notifications/{id}/read` | 단일 알림 읽음 처리 |
| | `DELETE` | `/api/notifications/clear-all` | 전체 알림 삭제 |
| | `DELETE` | `/api/notifications/{id}` | 단일 알림 삭제 |

---

## 🛡️ 예외 처리 포맷 규격 (Global Error Response)

모든 API에서 예외 발생 시 전역 예외 처리기를 통해 표준화된 JSON 구조를 반환합니다.

```json
{
  "success": false,
  "error": {
    "code": 404,
    "message": "요청하신 리소스를 찾을 수 없습니다."
  }
}
```
