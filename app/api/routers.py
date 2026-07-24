from fastapi import APIRouter
from app.api.endpoints import user
from app.api.endpoints import auth
from app.api.endpoints import cctv
from app.api.endpoints import monitoring
from app.api.endpoints import checklist
from app.api.endpoints import dashboard
from app.api.endpoints import chatbot
from app.api.endpoints import ai_detect
from app.api.endpoints import board
from app.api.endpoints import education
from app.api.endpoints import report
from app.api.endpoints import risk

api_router = APIRouter()

api_router.include_router(user.router, prefix="/users", tags=["users"])
api_router.include_router(user.admin_user_router, prefix="/admin/users", tags=["admin-users"])
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(cctv.router, prefix="/cctvs", tags=["cctvs"])
api_router.include_router(monitoring.router, prefix="/monitoring", tags=["monitoring"])
api_router.include_router(checklist.router, prefix="/checklists", tags=["checklists"])
api_router.include_router(dashboard.router, prefix="/dashboard", tags=["dashboard"])
api_router.include_router(chatbot.chatbot_router, prefix="/chatbot", tags=["chatbot"])
api_router.include_router(chatbot.data_router, prefix="/data", tags=["data"])
api_router.include_router(ai_detect.router, prefix="/ai", tags=["ai"])
api_router.include_router(board.router, prefix="/boards", tags=["boards"])
api_router.include_router(education.education_router, prefix="/education", tags=["education"])
api_router.include_router(education.admin_education_router, prefix="/admin/education", tags=["admin-education"])
api_router.include_router(report.router, prefix="/report", tags=["report"])
api_router.include_router(risk.router, prefix="/risk", tags=["risk"])
