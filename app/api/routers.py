from fastapi import APIRouter
from app.api.endpoints import user
from app.api.endpoints import auth
from app.api.endpoints import cctv
from app.api.endpoints import monitoring
from app.api.endpoints import checklist
from app.api.endpoints import dashboard
from app.api.endpoints import chatbot
from app.api.endpoints import ai_detect
from app.api.endpoints import board # 게시판(board) 라우터 추가

api_router = APIRouter()

api_router.include_router(user.router, prefix="/users", tags=["users"])
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(cctv.router, prefix="/cctvs", tags=["cctvs"])
api_router.include_router(monitoring.router, prefix="/monitoring", tags=["monitoring"])
api_router.include_router(checklist.router, prefix="/checklists", tags=["checklists"])
api_router.include_router(dashboard.router, prefix="/dashboard", tags=["dashboard"])
api_router.include_router(chatbot.chatbot_router, prefix="/chatbot", tags=["chatbot"])
api_router.include_router(chatbot.data_router, prefix="/data", tags=["data"])
api_router.include_router(ai_detect.router, prefix="/ai", tags=["ai"])
api_router.include_router(board.router, prefix="/boards", tags=["boards"]) # 게시판 라우터 추가