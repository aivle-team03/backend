import logging
from logging.handlers import RotatingFileHandler
import os
import traceback
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger("app")

def setup_logging():
    """파일 회전 로깅 설정 (logs/app.log 저장, 5MB 제한, 최대 5개 백업)"""
    os.makedirs("logs", exist_ok=True)
    
    log_formatter = logging.Formatter(
        "[%(asctime)s] [%(levelname)s] [%(name)s] [%(filename)s:%(lineno)d]: %(message)s"
    )
    
    # Rotating File Handler
    file_handler = RotatingFileHandler(
        "logs/app.log",
        maxBytes=5 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8"
    )
    file_handler.setFormatter(log_formatter)
    file_handler.setLevel(logging.INFO)
    
    # Console Handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(log_formatter)
    console_handler.setLevel(logging.INFO)
    
    # Root Logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    
    # 기존 등록되어 있을 수 있는 핸들러 중복 방지 위해 초기화 후 추가
    if root_logger.hasHandlers():
        root_logger.handlers.clear()
        
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)
    
    logger.info("어플리케이션 파일 기반 로깅 시스템 활성화 완료.")

def setup_exception_handlers(app: FastAPI):
    """FastAPI 전역 예외 처리 핸들러 마운트"""
    
    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException):
        logger.warning(
            f"HTTP 오류 발생 - 경로: {request.url.path} | 상태코드: {exc.status_code} | 메시지: {exc.detail}"
        )
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "success": False,
                "error": {
                    "code": exc.status_code,
                    "message": exc.detail
                }
            }
        )
        
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        details = exc.errors()
        logger.warning(
            f"요청 데이터 검증 실패(Pydantic) - 경로: {request.url.path} | 에러 내역: {details}"
        )
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "success": False,
                "error": {
                    "code": status.HTTP_422_UNPROCESSABLE_ENTITY,
                    "message": "요청 데이터의 포맷이 유효하지 않습니다. 입력값을 확인해 주세요.",
                    "details": details
                }
            }
        )
        
    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        logger.error(
            f"서버 내부 치명적 런타임 오류 발생 - 경로: {request.url.path} | 원인: {str(exc)}",
            exc_info=True
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "success": False,
                "error": {
                    "code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                    "message": "서버 내부 처리 중 예기치 못한 오류가 발생했습니다. 관리자에게 문의하세요."
                }
            }
        )
