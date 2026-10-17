-- ==============================================================================
-- [백선영] 수납·재정 대사 및 원무 창구 최적화 파트
--
-- 작업 목적: Silver 레이어 도메인별 그레인 단위 사전 집계 뷰 구축 SQL
-- 대상 테이블: payments, encounter_services
-- 대상 스키마: team3_medallion (Clean DB)
-- 주요 작업 내용:
--   1. 진료(encounter_id) 그레인 단위 사전 집계로 카테시안 곱(Fan-out) 원천 차단
--   2. 진료별 결제액/환불액 선집계 뷰(baek_silver_payment_totals) 생성
--   3. 환불-원결제 Self-Join 연결 검증 뷰(baek_silver_refund_links) 생성
-- ==============================================================================

-- ------------------------------------------------------------------------------
-- 1. [Silver 뷰 1] 진료별 결제·환불 집계 뷰 (baek_silver_payment_totals)
-- 설명: encounters 1건당 N건의 payments(결제, 환불)가 얽혀 있으므로,
--       진료(encounter_id) 그레인으로 사전 합산하여 1행으로 압축
-- ------------------------------------------------------------------------------
CREATE OR REPLACE VIEW team3_medallion.baek_silver_payment_totals AS
SELECT
    encounter_id,
    COUNT(*) AS transaction_rows,

    -- 결제 건수 및 환불 건수 분리 집계
    SUM(
        CASE
            WHEN CAST(transaction_type AS BINARY) = 'PAYMENT'
            THEN 1 ELSE 0
        END
    ) AS payment_rows,

    SUM(
        CASE
            WHEN CAST(transaction_type AS BINARY) = 'REFUND'
            THEN 1 ELSE 0
        END
    ) AS refund_rows,

    -- 결제 총액 및 환불 총액 분리 집계 (NULL 방지 COALESCE 처리)
    COALESCE(
        SUM(
            CASE
                WHEN CAST(transaction_type AS BINARY) = 'PAYMENT'
                THEN amount ELSE 0
            END
        ), 0
    ) AS paid_amount,

    COALESCE(
        SUM(
            CASE
                WHEN CAST(transaction_type AS BINARY) = 'REFUND'
                THEN amount ELSE 0
            END
        ), 0
    ) AS refunded_amount,

    -- 복합 결제 수단 검증 (단일 수단 여부 및 혼합 수단 플래그(Flag-SINGLE_CARD, MIXED...))
    COUNT(DISTINCT payment_method) AS method_count,
    MIN(payment_method) AS single_method_candidate,

    -- 시계열 정합성 검증용 최초/최종 거래 시각 추출
    MIN(
        CASE
            WHEN CAST(transaction_type AS BINARY) = 'PAYMENT'
            THEN payment_date ELSE NULL
        END
    ) AS first_payment_at,

    MAX(
        CASE
            WHEN CAST(transaction_type AS BINARY) = 'PAYMENT'
            THEN payment_date ELSE NULL
        END
    ) AS last_payment_at,

    MIN(payment_date) AS first_transaction_at,
    MAX(payment_date) AS last_transaction_at,

    -- 거래 유형 코드 유효성 검증(결제/환불 이외 유형 제거)
    SUM(
        CASE
            WHEN CAST(transaction_type AS BINARY) NOT IN ('PAYMENT', 'REFUND')
            THEN 1 ELSE 0
        END
    ) AS invalid_transaction_rows,

    -- 거래 일시 누락 검증
    SUM(
        CASE
            WHEN payment_date IS NULL
            THEN 1 ELSE 0
        END
    ) AS missing_transaction_time_rows

FROM team3_medallion.payments
GROUP BY encounter_id;


-- ------------------------------------------------------------------------------
-- 2. [Silver 뷰 2] 진료별 처방 서비스 집계 뷰 (baek_silver_service_totals)
-- 설명: encounters 1건당 M건의 처방 서비스(encounter_services)가 발생하므로,
--       진료(encounter_id) 그레인으로 처방액과 건수를 사전 합산
-- ------------------------------------------------------------------------------
CREATE OR REPLACE VIEW team3_medallion.baek_silver_service_totals AS
SELECT
    encounter_id,
    COUNT(*) AS service_rows,
    COALESCE(SUM(total_price), 0) AS service_amount,

    -- 비정상 서비스 금액(음수 등) 검출
    SUM(
        CASE
            WHEN total_price < 0
            THEN 1 ELSE 0
        END
    ) AS invalid_service_rows

FROM team3_medallion.encounter_services
GROUP BY encounter_id;


-- ------------------------------------------------------------------------------
-- 3. [Silver 뷰 3] 원결제-환불 1:1 연결 대사 뷰 (baek_silver_refund_links)
-- 설명: REFUND 거래의 original_payment_id가 유효한 선행 PAYMENT를 가리키는지 추적
-- ------------------------------------------------------------------------------
CREATE OR REPLACE VIEW team3_medallion.baek_silver_refund_links AS
SELECT
    r.payment_id AS refund_payment_id,
    r.encounter_id,
    r.amount AS refund_amount,
    r.payment_date AS refund_date,
    r.original_payment_id,
    p.payment_id AS matched_original_payment_id,
    p.amount AS original_paid_amount,
    p.payment_date AS original_payment_date,
    p.payment_method AS original_payment_method,

    -- 링크 정합성 상태 분류(진짜 정상 환불인지 여부)
    CASE
        WHEN r.original_payment_id IS NULL THEN 'MISSING_ORIGINAL_LINK'
        WHEN p.payment_id IS NULL THEN 'BROKEN_ORIGINAL_LINK'
        WHEN r.amount > p.amount THEN 'OVER_REFUND_AMOUNT'
        WHEN r.payment_date < p.payment_date THEN 'TIME_REVERSED_REFUND'
        ELSE 'VALID_REFUND_LINK'
    END AS refund_link_status

FROM team3_medallion.payments r
LEFT JOIN team3_medallion.payments p
    ON r.original_payment_id = p.payment_id
    AND CAST(p.transaction_type AS BINARY) = 'PAYMENT'
WHERE CAST(r.transaction_type AS BINARY) = 'REFUND';

