FROM python:3.14-slim

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
