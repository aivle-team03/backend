from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Optional

from app.schemas.chatbot import (
    ChatbotQueryRequest,
    ChatbotQueryResponse,
    RecommendationResponse,
    ManualSearchResponse
)
from app.crud.chatbot import (
    get_chatbot_recommendations,
    search_manuals_and_laws,
    process_chatbot_query
)

chatbot_router = APIRouter()
data_router = APIRouter()

# 1. 챗봇 관련 API
@chatbot_router.post("/query", response_model=ChatbotQueryResponse)
def post_chatbot_query(query_req: ChatbotQueryRequest):
    """안전 법규 및 사내 소방 매뉴얼 관련 챗봇 질의응답 API - 명세서 URL /api/chatbot/query (요구사항 USR-05-02-13)"""
    return process_chatbot_query(query_req)

@chatbot_router.get("/recommendations", response_model=RecommendationResponse)
def read_chatbot_recommendations():
    """초기 추천 질문 목록 조회 API - 명세서 URL /api/chatbot/recommendations (요구사항 USR-05-01-14)"""
    return get_chatbot_recommendations()

# 2. 매뉴얼/법규 검색 API
@data_router.get("/manuals", response_model=List[ManualSearchResponse])
def read_manuals(keyword: Optional[str] = None):
    """소방 및 산업 안전 매뉴얼/법규 검색 API - 명세서 URL /api/data/manuals (요구사항 ADM-15-56-7)"""
    return search_manuals_and_laws(keyword=keyword)
