from pydantic import BaseModel
from typing import List, Optional

class ChatbotQueryRequest(BaseModel):
    question_text: str
    history: Optional[List[str]] = []

class ChatbotQueryResponse(BaseModel):
    answer: str
    matched_keywords: List[str]

class RecommendationResponse(BaseModel):
    questions: List[str]

class ManualSearchResponse(BaseModel):
    title: str
    company_id: Optional[int] = None
    category: str
    content: str
    source: str

    class Config:
        orm_mode = True
