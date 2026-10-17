-- ==============================================================================
-- [백선영] 수납·재정 대사 및 원무 창구 최적화 파트
--
-- 작업 목적: Bronze 원천 데이터 프로파일링 및 1차 결함/중복 진단 SQL
-- 대상 테이블: payments (150.7만), encounters (100만), encounter_services (298만)
-- 대상 스키마: team3_medallion_dq (격리/제외 스키마), 원천 EMR 테이블
-- 주요 작업 내용:
--   1. 완전 동일 레코드 가짜 중복 제거(payments_excluded 7,501건) 탐지 및 분리
--   2. 미상값(UNREGISTERED 22,503건) 및 원천 구조 결함(88,006건) 격리 진단
--   3. 부모키 결함에 따른 2차 고아 레코드(reclean_quarantine) 연쇄 격리 규모 파악
-- ==============================================================================

-- ------------------------------------------------------------------------------
-- 1. [Bronze 무결성 진단] 원천 테이블 기본 레코드 건수 및 물리행 현황 파악
-- 목적: AS-IS 원천의 총 건수(1,152만 행) 중 핵심 3대 테이블의 물리행 확인
-- ------------------------------------------------------------------------------
SELECT 
    'encounters' AS table_name,
    COUNT(*) AS total_bronze_rows
FROM team3_medallion.encounters
UNION ALL
SELECT 
    'payments' AS table_name,
    COUNT(*) AS total_bronze_rows
FROM team3_medallion.payments
UNION ALL
SELECT 
    'encounter_services' AS table_name,
    COUNT(*) AS total_bronze_rows
FROM team3_medallion.encounter_services;


-- ------------------------------------------------------------------------------
-- 2. [완전 중복 제외 진단] PK 중복 및 전체 컬럼 동일 행 탐지 (Fan-out 원천 차단)
-- 목적: 네트워크 재전송 오류 등으로 인한 완전 동일 레코드 가짜 중복 제거 수치 진단
-- ------------------------------------------------------------------------------
SELECT 
    payment_id,
    COUNT(*) AS duplicate_count
FROM team3_medallion_dq.payments_raw_legacy -- 원천 데이터
GROUP BY payment_id
HAVING COUNT(*) > 1;

-- payments 테이블의 완전 중복 제외 확정 건수 확인 (기대값: 7,501건)
SELECT 
    'payments_excluded' AS target_table,
    COUNT(*) AS excluded_duplicate_rows
FROM team3_medallion_dq.payments_excluded;


-- ------------------------------------------------------------------------------
-- 3. [1차 원천 구조 결함 격리 진단] 센티널(더미) 키, 음수 금액, 부호/포맷 오류 탐지
-- 목적: 단일 행 자체의 데이터 오염(포맷 불일치, 화폐기호 혼입, 음수 금액) 검출
-- ------------------------------------------------------------------------------
-- (1) payments 1차 격리 사유별 전체 분포 확인 (기대값: 88,006건)
SELECT 
    quarantine_reason,
    COUNT(*) AS fault_row_count
FROM team3_medallion_dq.payments_quarantine
GROUP BY quarantine_reason
ORDER BY fault_row_count DESC;

-- (2) 결제수단 미등록 코드 검출: 'UNREGISTERED' 미상값이 정상값(CARD 등)으로 왜곡 대체되지 않고
--     원문 그대로 격리 장부(payments_quarantine)에 보존되었는지 무결성 검증
SELECT 
    quarantine_reason,
    payment_method,           -- 원천에 유입된 미등록 코드 문자열('UNREGISTERED') 전수 확인
    COUNT(*) AS fault_count
FROM team3_medallion_dq.payments_quarantine
WHERE quarantine_reason = 'UNREGISTERED_CODE:payment_method'
GROUP BY quarantine_reason, payment_method;

-- (3) 거래유형 미등록 코드 검출: 'UNREGISTERED' 미상값이 결제(PAYMENT)로 왜곡 대체되지 않고
--     원문 그대로 격리 장부(payments_quarantine)에 보존되었는지 무결성 검증
SELECT 
    quarantine_reason,
    transaction_type,         -- 원천에 유입된 미등록 코드 문자열('UNREGISTERED') 전수 확인
    COUNT(*) AS fault_count
FROM team3_medallion_dq.payments_quarantine
WHERE quarantine_reason = 'UNREGISTERED_CODE:transaction_type'
GROUP BY quarantine_reason, transaction_type;

-- (4) encounters 센티널 외래키(유령데이터 더미식별자 _999999999) 및 시간 역전(타임스탬프 오류) 탐지
SELECT 
    CASE 
        WHEN checkin_id LIKE '%999999999%' THEN 'SENTINEL_CHECKIN_KEY'
        WHEN started_at > ended_at THEN 'TIMESTAMP_REVERSED'
        WHEN gross_charge < 0 OR authorized_refund < 0 THEN 'NEGATIVE_CHARGE'
        ELSE 'OTHER_SYNTAX_ERROR'
    END AS error_category,
    COUNT(*) AS error_count
FROM team3_medallion_dq.encounters_quarantine
GROUP BY 1;


-- ------------------------------------------------------------------------------
-- 4. [2차 연쇄 결함 진단] 부모키 결함에 따른 고아 레코드(Orphan) 연쇄 격리 규모 파악
-- 아키텍처 원칙:
--   - 결함 있는 상위 부모(가짜 환자·오류 접수) 격리 시, 하위 결제 데이터까지 함께 
--     연쇄 분리하는 'Cascade 격리' 적용 
--     (※ Restrict 적용 시, 하위 결제 때문에 상위 결함 부모가 삭제 차단되어 Clean DB가 오염됨)
--   - 단, 결제는 실제 돈 기록이므로 영구 삭제하지 않고 감사 스키마(reclean_quarantine)에
--     원형 그대로 보존하는 'Zero-Drop 무손실 격리'를 채택.
-- ------------------------------------------------------------------------------
SELECT 
    quarantine_table_name,
    quarantine_stage,
    COUNT(*) AS isolated_row_count
FROM team3_medallion_dq.reclean_quarantine
WHERE quarantine_table_name IN ('payments', 'encounter_services', 'encounters')
GROUP BY quarantine_table_name, quarantine_stage
ORDER BY isolated_row_count DESC;

