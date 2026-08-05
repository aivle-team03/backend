@echo off
chcp 65001 > nul
echo ===================================================
echo   로컬 개발 서버 원클릭 실행기 (좀비 워커 방지 적용)
echo ===================================================

echo [0/3] 기존에 떠있는 좀비 파이썬 프로세스 청소 중...
echo Get-CimInstance Win32_Process ^| Where-Object { $_.Name -eq 'python.exe' -and ($_.CommandLine -match 'celery' -or $_.CommandLine -match 'uvicorn' -or $_.CommandLine -match 'watchfiles') } ^| ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue } > kill_zombies.ps1
powershell -ExecutionPolicy Bypass -File kill_zombies.ps1 >nul 2>&1
del kill_zombies.ps1 >nul 2>&1
timeout /t 2 >nul

echo [1/3] 백그라운드 Redis 컨테이너 시작...
docker compose up -d redis

echo [2/3] FastAPI 웹 서버 실행 (새 창)...
start "FastAPI Web Server" powershell -NoExit -Command "& { .\.venv\Scripts\Activate.ps1; python -m uvicorn app.main:app --reload }"

echo [3/3] Celery 비동기 워커 실행 (새 창, 코드 변경 시 자동 재시작)...
start "Celery Worker" powershell -NoExit -Command "& { .\.venv\Scripts\Activate.ps1; python -m watchfiles '.\.venv\Scripts\python.exe -m celery -A app.core.celery_app worker -l info -P solo' app/ }"

echo.
echo 모든 구형 좀비를 처치하고 새 서버가 성공적으로 켜졌습니다!
echo 이제 안심하고 테스트를 진행하세요.
echo.
pause
