# 🛡️ AI 기반 산업/소방 안전 모니터링 백엔드 API 시스템

![FastAPI](https://img.shields.io/badge/FastAPI-005571?style=for-the-badge&logo=fastapi)
![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)
![MySQL](https://img.shields.io/badge/MySQL-4479A1?style=for-the-badge&logo=mysql&logoColor=white)
![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-D71F00?style=for-the-badge&logo=sqlalchemy&logoColor=white)
![JWT](https://img.shields.io/badge/JWT-black?style=for-the-badge&logo=JSON%20web%20tokens)

> **AIVLE Team 03 백엔드 서비스**  
> 사업장 내 이상 상황(화재, 적치물, 보호구 미착용 등)을 실시간 모니터링하고, 현장 조치 체크리스트 전이 관리, 구역별 안전 위험도 계산, 소방 법규 챗봇 및 AI 조치 검증을 제공하는 RESTful 백엔드 API 서버입니다.

---

## 📌 주요 기능 (Key Features)

### 🔑 1. 인증/인가 및 사용자 관리 (`/api/auth`, `/api/users`)
- JWT Access/Refresh 토큰 기반 사용자 인증 및 비밀번호 Bcrypt 암호화
- 회원가입, 로그인, 아이디 중복 확인, 내 정보 및 사용자 목록 조회

### 📹 2. CCTV 모니터링 관리 (`/api/cctvs`)
- 구역별 CCTV 대수, 실시간 스트리밍 URL, 정상/비정상 작동 상태 관리 및 CRUD 제공

### 🚨 3. 이상 상황 모니터링 및 현장 조치 요청 (`/api/monitoring`)
- 이상 감지 이벤트 발생 이력 조회 및 모니터링
- 관리자가 이상 이벤트 발견 시 현장 조치자 지정 및 메시지 할당 ➡️ `Checklist` 조치 레코드 자동 생성

### 📋 4. 체크리스트 & 현장 조치 생명주기 관리 (`/api/checklists`)
- **상태 흐름**: `조치 대기` ➡️ `조치 중` ➡️ `승인 대기` ➡️ `승인 완료` (또는 `반려`)
- 현장 작업자의 조치 사진/설명 업로드 (`multipart/form-data`) 및 관리자 검토/승인 워크플로우
- 업로드 정적 자원 서빙 (`/static/uploads`)

### 📊 5. 대시보드 통계 & 종합 안전 등급 (`/api/dashboard`)
- **구역별 실시간 위험 지수**: CCTV 위치 단위 미해결 이벤트 비율 기반 위험도 연산 (0~100점)
- **종합 안전 등급 계산**: 최근 30일 이내 감지 이벤트의 미해결 상태별 감점 수식(100점 만점 척도) 적용 ➡️ **A ~ F 등급** 자동 산출 및 원인 분석 요약
- 기간별 통계 리포트 조회 및 AI 분석 보고서 요약 텍스트 제공

### 🤖 6. 소방안전 챗봇 & 법규/매뉴얼 검색 (`/api/chatbot`, `/api/data`)
- 소방/안전 키워드 기반 자연어 질의응답 매칭 엔진
- 초기 추천 질문 목록(4종) 제공
- 소방시설법, 산업안전보건법 및 사내 소방 매뉴얼 키워드 검색 지원

### 🧠 7. AI 비전 탐지 & 조치 결과 검증 (`/api/ai`)
- **소방시설 탐지**: 이미지 내 소화기 등의 바운딩 박스(`bbox`) 및 신뢰도 탐지
- **위험요소 탐지**: 비상구 통로 불법 적치물/장애물 검지 및 위험 수준(`High`/`Low`) 판정
- **화재 징후 탐지**: CCTV 프레임(이미지) 내 농연(Smoke) 및 불꽃 징후 감지 및 비상 경보 메시지 리턴
- **조치결과 재확인**: 조치 전/후 사진 2장을 수신하여 시각적 유사도 분석 및 위험 요소 해결 여부 AI 검증

### ⚙️ 8. 글로벌 예외 처리 & 파일 로깅 시스템
- 서버 전역 예외(`HTTPException`, `RequestValidationError`, `Exception`)를 통일된 JSON 구조로 가공하여 전달
- `RotatingFileHandler` 기반 `logs/app.log` 로그 자동 적재 및 관리 (5MB 백업 파일 회전)
- 프론트엔드 크로스 도메인 연동 지원을 위한 **CORS 미들웨어** 탑재

---

## 🛠 기술 스택 (Tech Stack)

| 구분 | 기술 / 라이브러리 |
| :--- | :--- |
| **Language** | Python 3.10+ |
| **Framework** | FastAPI |
| **Database & ORM** | MySQL, SQLAlchemy, PyMySQL |
| **Auth & Security** | PyJWT, Passlib (Bcrypt), Python-Multipart |
| **Validation** | Pydantic v2 |
| **Server Engine** | Uvicorn, WatchFiles |

---

## 📂 프로젝트 구조 (Directory Structure)

```text
big_project/
├── app/
│   ├── api/
│   │   ├── endpoints/        # API 라우터 컨트롤러 (auth, cctv, chatbot, checklist, dashboard, monitoring, user, ai_detect)
│   │   └── routers.py        # 통합 API 라우터 매핑
│   ├── core/                 # 암호화(crypt), 전역 예외/로깅(exceptions)
│   ├── crud/                 # DB 비즈니스 로직 / CRUD
│   ├── db/                   # DB 연결 세션 및 Base 선언
│   ├── models/               # SQLAlchemy ORM 모델 (User, CCTV, Event, Checklist, Report, Map 등)
│   ├── schemas/              # Pydantic DTO 데이터 스키마
│   └── main.py               # FastAPI 애플리케이션 엔트리포인트
├── logs/                     # 서버 런타임 회전 파일 로그 (app.log)
├── static/uploads/           # 현장 조치 업로드 이미지 서빙 디렉토리
├── seed.py                   # DB 자동 시딩 스크립트 (더미 데이터 일괄 적재)
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
DATABASE_URL="mysql+pymysql://<DB_USER>:<DB_PASSWORD>@<DB_HOST>:3306/<DB_NAME>"
SECRET_KEY="your-secret-key"
ALGORITHM="HS256"
ACCESS_TOKEN_EXPIRE_MINUTES=30
```

### 3. 데이터베이스 초기 시딩 (Optional)

개발 및 테스트용 모의 데이터(CCTV 4대, 이상 이벤트 12건, 조치 체크리스트 10건, 리포트 등)를 일괄적재합니다.

```bash
python seed.py
```

### 4. 서버 기동

```bash
uvicorn app.main:app --reload
```

- **API 서버 주소**: `http://127.0.0.1:8000`
- **Swagger API 문서**: `http://127.0.0.1:8000/docs`
- **ReDoc API 문서**: `http://127.0.0.1:8000/redoc`

---

## 📋 API 엔드포인트 명세 요약 (API Reference)

| Category | Method | Endpoint | Description |
| :--- | :---: | :--- | :--- |
| **Auth** | `POST` | `/api/auth/login` | 로그인 및 JWT 토큰 발급 |
| | `POST` | `/api/auth/signup` | 신규 회원가입 |
| | `GET` | `/api/auth/checkid` | 사용자 아이디 중복 확인 |
| **Users** | `GET` | `/api/users/me` | 내 정보 조회 |
| | `GET` | `/api/users/` |전체 사용자 목록 조회 |
| **CCTV** | `GET` | `/api/cctvs/` | CCTV 목록 및 상태 조회 |
| | `POST` | `/api/cctvs/` | 신규 CCTV 등록 |
| | `GET` | `/api/cctvs/{camera_id}` | 특정 CCTV 상세 조회 |
| **Monitoring** | `GET` | `/api/monitoring/events` | 이상 감지 이벤트 목록 조회 |
| | `POST` | `/api/monitoring/events/{event_id}/request` | 현장 조치 요청 (체크리스트 생성) |
| **Checklist** | `GET` | `/api/checklists/` | 전체 체크리스트 목록 조회 |
| | `GET` | `/api/checklists/my` | 내 조치 할당 목록 조회 |
| | `POST` | `/api/checklists/{id}/report` | 현장 조치 사진/내용 업로드 완료 보고 |
| | `PATCH` | `/api/checklists/{id}/status` | 관리자 검토 (승인 완료 / 반려) |
| **Dashboard**| `GET` | `/api/dashboard/zones/stats` | 구역별 위험도 집계 통계 |
| | `GET` | `/api/dashboard/safetygrade` | 30일 이내 이벤트 기반 종합 안전 등급 (A~F) |
| | `GET` | `/api/dashboard/reports` | 기간별 통계 보고서 조회 |
| | `GET` | `/api/dashboard/reports/summary` | 보고서 AI 분석 요약 |
| **Chatbot** | `POST` | `/api/chatbot/query` | 안전 질의응답 챗봇 |
| | `GET` | `/api/chatbot/recommendations` | 추천 질문 목록 (4종) |
| **Data** | `GET` | `/api/data/manuals` | 소방법/산업안전 매뉴얼 검색 |
| **AI Detect** | `POST` | `/api/ai/detect/facilities` | 소방시설 바운딩박스 탐지 |
| | `POST` | `/api/ai/detect/hazards` | 불법 적치물/위험요소 탐지 |
| | `POST` | `/api/ai/detect/fire` | 화재 및 연기(Smoke) 징후 탐지 |
| | `POST` | `/api/ai/verify-action` | 조치 전/후 사진 시각 유사도 AI 검증 |

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
