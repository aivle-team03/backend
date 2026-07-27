import sys
import os
from fastapi.testclient import TestClient

# Add project root to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.main import app

client = TestClient(app)


def test_safety_manager_workflow():
    print("==================================================")
    print("[TEST] Safety Manager Page & Invite Code Flow Test")
    print("==================================================")

    # 1. 안전관리자(admin) 로그인
    login_resp = client.post("/api/auth/login", json={
        "user_id": "admin",
        "password": "admin123"
    })
    assert login_resp.status_code == 200, f"로그인 실패: {login_resp.json()}"
    admin_token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {admin_token}"}
    print("[SUCCESS] 1. Safety Manager (admin) Login Successful")

    # 2. 카테고리 목록 조회 (/api/admin/categories)
    cat_resp = client.get("/api/admin/categories", headers=headers)
    assert cat_resp.status_code == 200, f"카테고리 조회 실패: {cat_resp.json()}"
    categories = cat_resp.json()["categories"]
    print(f"[SUCCESS] 2. Category list fetched: {categories}")
    assert "지게차" in categories and "화물트럭" in categories

    # 3. 일반유저용 회원가입 코드 생성 (/api/admin/invite-codes)
    code_resp1 = client.post("/api/admin/invite-codes", headers=headers, json={
        "role": "일반유저",
        "category": "지게차"
    })
    assert code_resp1.status_code == 200, f"일반유저 코드 생성 실패: {code_resp1.json()}"
    code_data1 = code_resp1.json()
    forklift_code = code_data1["code"]
    print(f"[SUCCESS] 3. General user (Forklift) invite code generated: {forklift_code} (Role: {code_data1['role']}, Category: {code_data1['category']})")

    # 4. 관제사용 회원가입 코드 생성
    code_resp2 = client.post("/api/admin/invite-codes", headers=headers, json={
        "role": "관제사"
    })
    assert code_resp2.status_code == 200, f"관제사 코드 생성 실패: {code_resp2.json()}"
    controller_code = code_resp2.json()["code"]
    print(f"[SUCCESS] 4. Controller invite code generated: {controller_code}")

    # 5. 전체 발급 코드 목록 조회 (/api/admin/invite-codes)
    codes_list_resp = client.get("/api/admin/invite-codes", headers=headers)
    assert codes_list_resp.status_code == 200
    print(f"[SUCCESS] 5. Total generated codes count: {len(codes_list_resp.json())}")

    # 6. 회원가입 코드 유효성 검증 (/api/auth/verify-code)
    verify_resp = client.get(f"/api/auth/verify-code?code={forklift_code}")
    assert verify_resp.status_code == 200, f"코드 검증 실패: {verify_resp.json()}"
    assert verify_resp.json()["role"] == "일반유저"
    assert verify_resp.json()["category"] == "지게차"
    print(f"[SUCCESS] 6. Signup code pre-verification: {verify_resp.json()}")

    # 7. 신규 유저가 회원가입 코드를 입력하여 회원가입 (/api/auth/signup)
    signup_resp = client.post("/api/auth/signup", json={
        "user_id": "forklift_driver_01",
        "name": "홍길동",
        "password": "password123!",
        "code": forklift_code,
        "company_code": "AIVLE_TEAM03"
    })
    assert signup_resp.status_code == 200, f"회원가입 실패: {signup_resp.json()}"
    signup_data = signup_resp.json()
    assert signup_data["role"] == "일반유저"
    assert signup_data["category"] == "지게차"
    print(f"[SUCCESS] 7. User Registration with Invite Code - Role: {signup_data['role']}, Category: {signup_data['category']}")

    # 8. 이미 사용된 코드 재사용 시도 ➡️ 400 Bad Request 에러 검증
    reuse_resp = client.post("/api/auth/signup", json={
        "user_id": "forklift_driver_02",
        "name": "김철수",
        "password": "password123!",
        "code": forklift_code,
        "company_code": "AIVLE_TEAM03"
    })
    assert reuse_resp.status_code == 400
    err_msg = reuse_resp.json().get("error", {}).get("message", str(reuse_resp.json()))
    print(f"[SUCCESS] 8. Re-use prevention verified: {err_msg}")


    # 9. 안전관리자의 전체 유저 목록 조회 (/api/admin/users)
    users_resp = client.get("/api/admin/users", headers=headers)
    assert users_resp.status_code == 200
    all_users = users_resp.json()
    new_user = next((u for u in all_users if u["user_id"] == "forklift_driver_01"), None)
    assert new_user is not None
    print(f"[SUCCESS] 9. Admin view all users (New User UID: {new_user['uid']}, Category: {new_user['category']})")

    # 10. 안전관리자가 일반유저의 카테고리를 변경 (지게차 -> 화물트럭) (/api/admin/users/{uid})
    update_resp = client.patch(f"/api/admin/users/{new_user['uid']}", headers=headers, json={
        "category": "화물트럭"
    })
    assert update_resp.status_code == 200, f"카테고리 수정 실패: {update_resp.json()}"
    updated_user = update_resp.json()
    assert updated_user["category"] == "화물트럭"
    print(f"[SUCCESS] 10. Admin updated General User Category: {new_user['category']} -> {updated_user['category']}")

    # 11. 수정된 일반유저 계정으로 로그인 후 내 정보 조회 (/api/users/me)
    user_login = client.post("/api/auth/login", json={
        "user_id": "forklift_driver_01",
        "password": "password123!"
    })
    user_token = user_login.json()["access_token"]
    me_resp = client.get("/api/users/me", headers={"Authorization": f"Bearer {user_token}"})
    assert me_resp.status_code == 200
    assert me_resp.json()["category"] == "화물트럭"
    print(f"[SUCCESS] 11. General User /me response reflects updated category: '화물트럭'")

    print("==================================================")
    print("ALL TESTS PASSED SUCCESSFULLY!")
    print("==================================================")


if __name__ == "__main__":
    test_safety_manager_workflow()
