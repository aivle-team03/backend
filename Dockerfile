FROM python:3.14-slim

# 시스템 의존성 설치 (ffmpeg 등 영상 처리를 위해 필요할 수 있음)
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libsm6 \
    libxext6 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 파이썬 의존성 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 앱 소스 복사
COPY . .

# FastAPI 서버가 사용할 포트
EXPOSE 8000

# 컨테이너 실행 기본 명령어 (docker-compose에서 덮어쓰기됨)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
