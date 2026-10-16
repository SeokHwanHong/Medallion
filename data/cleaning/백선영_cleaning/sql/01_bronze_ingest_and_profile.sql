-- ==============================================================================
-- [Bronze Layer] 원천 데이터 수집 프로파일링 및 1차 결함 검증 쿼리
-- 프로젝트: 외래 EMR 병원 데이터 AI-Ready 정제 및 수납 정합성 검증
-- 작성 레이어: Bronze (원천 수집 및 AS-IS 품질 진단)
-- 대상 DB 스키마: team3_medallion_dq (격리/제외) / 원천 EMR 레거시 테이블
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
-- 목적: 네트워크 재전송 오류 등으로 인한 완전 동일 레코드(payments_excluded) 수치 진단
-- ------------------------------------------------------------------------------
SELECT 
    payment_id,
    COUNT(*) AS duplicate_count
FROM team3_medallion_dq.payments_raw_legacy -- 또는 Bronze 원천
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
-- (1) payments 1차 격리 사유별 분포 확인 (기대값: 88,006건)
SELECT 
    quarantine_reason,
    COUNT(*) AS fault_row_count
FROM team3_medallion_dq.payments_quarantine
GROUP BY quarantine_reason
ORDER BY fault_row_count DESC;

-- (2) encounters 센티널 외래키(미등록 부모키 _999999999) 및 시간 역전 탐지
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
-- 목적: 부모(encounters)가 격리됨으로써 참조 무결성이 파괴된 2차 결함 행 집계
-- ------------------------------------------------------------------------------
SELECT 
    quarantine_table_name,
    quarantine_stage,
    COUNT(*) AS isolated_row_count
FROM team3_medallion_dq.reclean_quarantine
WHERE quarantine_table_name IN ('payments', 'encounter_services', 'encounters')
GROUP BY quarantine_table_name, quarantine_stage
ORDER BY isolated_row_count DESC;

