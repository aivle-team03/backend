# 회사 삭제 연쇄 삭제 검증

이 폴더는 회사를 완전 삭제할 때 해당 회사가 소유한 DB 데이터가
외래키 규칙에 따라 함께 삭제되는지 검증합니다.

## 검증 대상

`test_company_delete_cascade.py`는 다음 동작을 확인합니다.

1. 회사를 삭제하면 회사에 직접 연결된 데이터가 모두 삭제되는지 확인합니다.
   - 사용자와 회원가입 코드
   - CCTV, 이벤트와 이벤트 카테고리
   - 체크리스트와 게시글
   - 교육과 교육 이수 상태
   - 점검과 점검 이력
   - 조치 이력
   - 보고서와 보고서 매핑 데이터
2. 삭제 대상이 아닌 다른 회사의 데이터가 유지되는지 확인합니다.
3. 사용자를 먼저 삭제해도 게시글, 보고서, 조치 이력 같은 증적은 남고
   사용자 외래키만 `NULL`로 변경되는지 확인합니다.
4. 사용자 참조가 해제된 상태에서도 회사 연쇄 삭제가 정상 동작하는지
   확인합니다.

## 테스트 실행 방법

백엔드 프로젝트 루트에서 다음 명령을 실행합니다.

```bash
cd /Users/hyeokjae/Desktop/BP3/backend

PYTHONPYCACHEPREFIX=/private/tmp/bp3_pycache \
.venv/bin/python -m unittest discover \
  -s tests/deletion \
  -p "test_*.py" \
  -v
```

특정 테스트 파일만 실행하려면 다음 명령을 사용합니다.

```bash
PYTHONPYCACHEPREFIX=/private/tmp/bp3_pycache \
.venv/bin/python -m unittest \
  tests.deletion.test_company_delete_cascade \
  -v
```

## 정상 결과

두 테스트가 모두 `ok`로 끝나고 마지막에 `OK`가 표시되어야 합니다.

```text
test_deleting_company_removes_all_owned_rows ... ok
test_user_reference_rules_do_not_block_company_cascade ... ok

Ran 2 tests
OK
```

## 테스트 DB 범위

이 테스트는 기본적으로 실행할 때마다 새로 생성되는 메모리 SQLite를
사용합니다. 따라서 원격 MySQL이나 운영 데이터를 수정하지 않습니다.

테스트가 검증하는 것은 SQLAlchemy 모델에 선언된 `CASCADE`와 `SET NULL`
규칙입니다. 실제 원격 MySQL에 마이그레이션이 적용됐는지는 별도로
확인해야 합니다.

## 실제 MySQL 적용 확인

원격 DB 연결을 복구한 후 다음 마이그레이션을 먼저 실행합니다.

```text
migrations/20260730_company_delete_cascade.sql
```

그다음 운영 데이터가 아닌 테스트 회사를 준비하고 트랜잭션 안에서
삭제를 검증합니다.

```sql
START TRANSACTION;

DELETE FROM company
WHERE company_id = 테스트_회사_ID;

-- 관련 테이블의 잔여 데이터와 다른 회사 데이터 유지 여부 확인

ROLLBACK;
```

모든 결과가 정상일 때만 실제 삭제 작업에서 `COMMIT`합니다.

## 주의사항

- 실제 회사 데이터로 처음 검증하지 않습니다.
- 마이그레이션 실행 전에 DB를 백업합니다.
- `FOREIGN_KEY_CHECKS=0`으로 강제 삭제하지 않습니다.
- 이 테스트는 이미지와 영상 같은 실제 파일 삭제를 검증하지 않습니다.
