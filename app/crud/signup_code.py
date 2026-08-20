import secrets
import string
from typing import List, Optional
from sqlalchemy.orm import Session
from app.models.signup_code import SignupCode
from app.utils.datetime_utils import get_kst_now

DEFAULT_CATEGORIES = [
    "지게차", "화물트럭", "토잉카", "팔레트",
    "적재", "현장보조", "유지보수", "재고", "위험물", "공통"
]



SIGNUP = "signup"
PASSWORD_RESET = "password_reset"

# 재설정 코드 유효 시간. 길게 두면 사실상 상시 비밀번호가 된다.
RESET_CODE_TTL_HOURS = 24


def generate_unique_code(db: Session, length: int = 8, prefix: str = "INV") -> str:
    """고유 무작위 코드 생성 (가입 INV-X8K2M9N4 / 재설정 RST-X8K2M9N4)"""
    alphabet = string.ascii_uppercase + string.digits
    while True:
        random_str = ''.join(secrets.choice(alphabet) for _ in range(length))
        code = f"{prefix}-{random_str}"
        existing = db.query(SignupCode).filter(SignupCode.code == code).first()
        if not existing:
            return code


def create_signup_code(db: Session, company_id: int, role: str, category: Optional[str] = None) -> SignupCode:
    """새로운 회원가입 코드 생성 및 저장"""
    code_str = generate_unique_code(db)
    
    # 일반유저가 아니면 카테고리 None 처리
    if role != "일반유저":
        category = None

    db_code = SignupCode(
        company_id=company_id,
        code=code_str,
        purpose=SIGNUP,
        role=role,
        category=category,
        is_used=False,
        created_at=get_kst_now(),
    )
    db.add(db_code)
    db.commit()
    db.refresh(db_code)
    return db_code


def get_all_signup_codes(db: Session, company_id: int) -> List[SignupCode]:
    """생성된 전체 회원가입 코드 목록 조회"""
    return (
        db.query(SignupCode)
        .filter(SignupCode.company_id == company_id)
        .order_by(SignupCode.id.desc())
        .all()
    )


def get_signup_code_by_code(db: Session, code: str) -> Optional[SignupCode]:
    """코드 문자열로 회원가입 코드 정보 조회.

    가입용만 돌려준다. 재설정 코드가 가입 화면의 코드 확인에서 통과하면 안 된다.
    """
    return (
        db.query(SignupCode)
        .filter(SignupCode.code == code, SignupCode.purpose == SIGNUP)
        .first()
    )


def get_available_categories() -> List[str]:
    """선택 가능한 유저 장비 카테고리 목록 리턴"""
    return DEFAULT_CATEGORIES


def create_password_reset_code(db: Session, company_id: int, target_uid: int) -> SignupCode:
    """관리자가 특정 사용자에게 발급하는 1회용 비밀번호 재설정 코드.

    기존 가입 코드를 되살리지 않고 매번 새 행을 만든다. 가입 코드는 이미 전달돼
    노출된 값이고, 되돌리면 가입 이력까지 사라진다.

    used_by_uid 에 대상 사용자를 미리 넣는다. 대상이 없으면 코드를 아는 사람이
    아무 계정이나 바꿀 수 있어 지금 문제를 그대로 옮겨오게 된다.
    """
    db_code = SignupCode(
        company_id=company_id,
        code=generate_unique_code(db, prefix="RST"),
        purpose=PASSWORD_RESET,
        role="",          # 재설정 코드는 권한을 부여하지 않는다
        category=None,
        is_used=False,
        used_by_uid=target_uid,
        created_at=get_kst_now(),
    )
    db.add(db_code)
    db.commit()
    db.refresh(db_code)
    return db_code


def consume_password_reset_code(db: Session, code: str, target_uid: int) -> bool:
    """재설정 코드를 검증하고 소비한다. 성공하면 True.

    용도·대상·사용여부·만료를 모두 본다. 하나라도 어긋나면 실패로 처리해
    어느 조건에서 걸렸는지 밖으로 흘리지 않는다.
    """
    row = (
        db.query(SignupCode)
        .filter(
            SignupCode.code == code,
            SignupCode.purpose == PASSWORD_RESET,
            SignupCode.is_used == False,
            SignupCode.used_by_uid == target_uid,
        )
        .first()
    )
    if not row:
        return False

    age = get_kst_now() - row.created_at
    if age.total_seconds() > RESET_CODE_TTL_HOURS * 3600:
        return False

    row.is_used = True
    db.commit()
    return True
