from app.schemas.chatbot import ChatbotQueryRequest


MANUALS_DB = [
    {
        "title": "소화기 사용법 및 정기 점검 가이드",
        "category": "소방 점검",
        "content": "소화기 사용법: 1. 안전핀을 뽑는다. 2. 노즐을 화원으로 향한다. 3. 손잡이를 움켜쥔다. 4. 바람을 등지고 빗자루 쓸듯 쏜다. 점검 주기: 월 1회 외관 점검, 10년 경과 시 폐기 또는 성능 확인 필요.",
        "source": "소방청 화재안전기준(NFSC)"
    },
    {
        "title": "비상구 및 피난시설 적치물 금지 규정",
        "category": "소방법 규정",
        "content": "소방시설법 제10조(피난시설, 방화구획 및 방화시설의 유지·관리): 피난시설 및 방화구획 주위에 물건을 쌓아두거나 장애물을 설치해서는 안 되며, 위반 시 최대 300만 원 이하의 과태료가 부과됩니다.",
        "source": "소방시설 설치 및 관리에 관한 법률"
    },
    {
        "title": "화재 발생 시 피난 대피 요령",
        "category": "화재 대피",
        "content": "1. 젖은 수건 등으로 코와 입을 막고 낮은 자세로 이동합니다. 2. 비상계단을 이용하여 하향 또는 옥상으로 대피하며 엘리베이터는 절대 탑승하지 않습니다. 3. 비상벨을 누르고 큰 소리로 불이야 외쳐 주변에 알립니다.",
        "source": "행정안전부 국민행동요령"
    },
    {
        "title": "산업안전보건법상 보호구 착용 의무 기준",
        "category": "산업 안전",
        "content": "산업안전보건법 제38조(안전조치): 사업주는 추락 위험, 물체의 낙하·비래 위험이 있는 작업장에서 안전모, 안전화 등 적절한 개인보호구를 작업자에게 지급하고 착용하도록 관리·감독해야 합니다. 작업자 미착용 시 과태료 처분을 받을 수 있습니다.",
        "source": "산업안전보건법"
    }
]

def get_chatbot_recommendations():
    return {
        "questions": [
            "소화기 사용법과 점검 주기는 어떻게 되나요?",
            "비상구 및 피난 통로에 물건을 적치하면 어떤 처벌을 받나요?",
            "화재 발생 시 대피 요령과 행동 강령을 알려주세요.",
            "작업장 안전모 착용 의무에 대한 산업안전보건법 기준은 무엇인가요?"
        ]
    }

def search_manuals_and_laws(keyword: str):
    if not keyword:
        return MANUALS_DB
    keyword_lower = keyword.lower()
    return [
        item for item in MANUALS_DB
        if keyword_lower in item["title"].lower() or keyword_lower in item["content"].lower()
    ]

def process_chatbot_query(query_req: ChatbotQueryRequest):
    question_text = query_req.question_text
    history = query_req.history
    
    question_text_lower = question_text.lower()
    matched_keywords = []
    answer = ""
    
    if any(k in question_text_lower for k in ["소화기", "소화"]):
        matched_keywords.append("소화기")
        answer += "[소화기 가이드]\n" + MANUALS_DB[0]["content"] + "\n\n"
        
    if any(k in question_text_lower for k in ["비상구", "적치", "장애물"]):
        matched_keywords.append("비상구")
        answer += "[비상구 규정]\n" + MANUALS_DB[1]["content"] + "\n\n"
        
    if any(k in question_text_lower for k in ["화재", "대피", "피난"]):
        matched_keywords.append("대피요령")
        answer += "[대피 행동강령]\n" + MANUALS_DB[2]["content"] + "\n\n"
        
    if any(k in question_text_lower for k in ["안전모", "안전화", "보호구", "장구"]):
        matched_keywords.append("개인보호구")
        answer += "[보호구 착용의무]\n" + MANUALS_DB[3]["content"] + "\n\n"
        
    if not answer:
        answer = "죄송합니다. 소방 안전 매뉴얼 또는 법규와 관련된 질문을 입력해 주세요. (예: 소화기 사용법, 비상구 관리 기준 등)"
        
    return {
        "answer": answer.strip(),
        "matched_keywords": matched_keywords
    }
