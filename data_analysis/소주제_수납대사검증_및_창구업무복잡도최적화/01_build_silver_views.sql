-- =========================================================
-- [백선영] 02_build_silver.sql
-- 병원 결제·환불 분석을 위한 기초 집계 VIEW
--
-- 대상: MySQL 8.4 / team3_medallion, team3_medallion_dq
-- 원본 업무 테이블의 데이터를 수정하지 않는다.
-- CREATE VIEW 권한이 필요하며 읽기 전용 트랜잭션 밖에서 실행한다.
-- 기존 VIEW와 이름이 겹치면 중단한다. 자동 교체하지 않는다.
-- 실제 컬럼과 부모 PK 유일성을 확인한 뒤 실행한다.
--
-- CAST(... AS BINARY):
-- 코드의 대소문자와 후행 공백을 엄격하게 구분한다.
-- 연결 끊김이나 쿼리 성능을 해결하는 설정은 아니다.
-- =========================================================


-- =========================================================
-- 1. 진료별 결제·환불 집계
-- 서비스 상세와 결제를 각각 집계하여 다중 조인 증폭 방지
-- =========================================================

-- 오토커밋 해제
SET SESSION autocommit = 0;

-- 읽기 전용 분석 시작 CTE, VIEW 위주 분석하기로.
START TRANSACTION WITH CONSISTENT SNAPSHOT, READ ONLY;

-- 분석 중 다른 세션이 데이터를 변경해도 같은 스냅샷으로 조회하고,
-- 현재 트랜잭션에서는 업무 데이터 변경을 제한.
START TRANSACTION WITH CONSISTENT SNAPSHOT, READ ONLY; 

CREATE VIEW team3_medallion.baek_silver_payment_totals AS
SELECT
    encounter_id,
    COUNT(*) AS transaction_rows,

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

    COUNT(
        DISTINCT CASE
            WHEN CAST(transaction_type AS BINARY) = 'PAYMENT'
            THEN payment_method
        END
    ) AS method_count,

    MIN(
        CASE
            WHEN CAST(transaction_type AS BINARY) = 'PAYMENT'
            THEN payment_method
        END
    ) AS single_method_candidate,

    SUM(
        CASE
            WHEN CAST(transaction_type AS BINARY) = 'PAYMENT'
                 AND amount > 0
            THEN amount ELSE 0
        END
    ) AS paid_amount,

    SUM(
        CASE
            WHEN CAST(transaction_type AS BINARY) = 'REFUND'
                 AND amount > 0
            THEN amount ELSE 0
        END
    ) AS refunded_amount,

    SUM(
        CASE
            WHEN amount IS NULL
              OR amount <= 0
              OR transaction_type IS NULL
              OR CAST(transaction_type AS BINARY)
                    NOT IN ('PAYMENT', 'REFUND')
              OR payment_method IS NULL
              OR CAST(payment_method AS BINARY)
                    NOT IN ('CARD', 'CASH', 'TRANSFER')
              OR source_system IS NULL
              OR CAST(source_system AS BINARY)
                    NOT IN ('LEGACY_A', 'LEGACY_B')
            THEN 1 ELSE 0
        END
    ) AS invalid_transaction_rows,

    MIN(
        CASE
            WHEN CAST(transaction_type AS BINARY) = 'PAYMENT'
            THEN transacted_at
        END
    ) AS first_payment_at,

    MAX(
        CASE
            WHEN CAST(transaction_type AS BINARY) = 'PAYMENT'
            THEN transacted_at
        END
    ) AS last_payment_at,

    MIN(transacted_at) AS first_transaction_at,
    MAX(transacted_at) AS last_transaction_at,

    SUM(
        CASE WHEN transacted_at IS NULL THEN 1 ELSE 0 END
    ) AS missing_transaction_time_rows

FROM team3_medallion.payments
GROUP BY encounter_id;


-- =========================================================
-- 2. 진료별 서비스 상세 집계
-- 명세서 기준 수량·단가·줄 금액·카탈로그 유효기간 확인
-- 부모 PK가 유일해야 조인으로 상세행이 늘어나지 않는다.
-- =========================================================

CREATE VIEW team3_medallion.baek_silver_service_totals AS
SELECT
    es.encounter_id,
    COUNT(*) AS service_rows,
    SUM(es.line_amount) AS service_amount,

    SUM(
        CASE
            WHEN es.quantity IS NULL
              OR es.unit_price IS NULL
              OR es.line_amount IS NULL
              OR es.quantity <= 0
              OR es.unit_price <= 0
              OR es.line_amount <> es.quantity * es.unit_price
              OR sc.service_version_id IS NULL
              OR sc.unit_price IS NULL
              OR sc.unit_price <= 0
              OR es.unit_price <> sc.unit_price
              OR sc.valid_from IS NULL
              OR sc.valid_to IS NULL
              OR sc.valid_from > sc.valid_to
              OR e.encounter_id IS NULL
              OR e.started_at IS NULL
              OR DATE(e.started_at) < sc.valid_from
              OR DATE(e.started_at) > sc.valid_to
            THEN 1 ELSE 0
        END
    ) AS invalid_service_rows

FROM team3_medallion.encounter_services AS es

LEFT JOIN team3_medallion.service_catalog AS sc
    ON sc.service_version_id = es.service_version_id

LEFT JOIN team3_medallion.encounters AS e
    ON e.encounter_id = es.encounter_id

GROUP BY es.encounter_id;


-- =========================================================
-- 3. 격리 결제의 연결용 키
-- 격리 원본은 그대로 두고 조회 결과에 연결용 키만 추가한다.
-- 공백 제거·하이픈 치환 후 ID 형식이 맞는 경우만 연결한다.
-- 연결 가능한 키라는 뜻이며, 정상 데이터라는 뜻은 아니다.
-- =========================================================

CREATE VIEW team3_medallion.baek_silver_quarantine_payment_keys AS
SELECT
    q.*,

    CASE
        WHEN REGEXP_LIKE(
            REPLACE(TRIM(encounter_id), '-', '_'),
            '^ENC_[0-9]{9}$',
            'c'
        )
        THEN REPLACE(TRIM(encounter_id), '-', '_')
    END AS linked_encounter_id,

    CASE
        WHEN REGEXP_LIKE(
            REPLACE(TRIM(original_payment_id), '-', '_'),
            '^PAY_[0-9]{9}$',
            'c'
        )
        THEN REPLACE(TRIM(original_payment_id), '-', '_')
    END AS linked_original_payment_id

FROM team3_medallion_dq.payments_quarantine AS q;


-- =========================================================
-- 4. 진료별 연결 가능한 격리 결제 건수
-- 연결 불가능한 격리행은 아래 별도 진단에서 확인한다.
-- =========================================================

CREATE VIEW team3_medallion.baek_silver_qpayment_totals AS
SELECT
    linked_encounter_id AS encounter_id,
    COUNT(*) AS quarantine_payment_rows

FROM team3_medallion.baek_silver_quarantine_payment_keys

WHERE linked_encounter_id IS NOT NULL

GROUP BY linked_encounter_id;


-- =========================================================
-- 5. 진료별 격리 서비스 상세 건수
-- DQ 테이블의 분류 의미는 팀의 적재 명세와 대조해야 한다.
-- =========================================================

CREATE VIEW team3_medallion.baek_silver_qservice_totals AS
SELECT
    encounter_id,
    COUNT(*) AS quarantine_service_rows

FROM team3_medallion_dq.encounter_services

GROUP BY encounter_id;


-- =========================================================
-- 6. 진료의 병원·진료과 연결 정보
-- LEFT JOIN으로 연결 실패 진료를 모집단에 보존한다.
-- 병원·진료과 미분류는 실제 기관명으로 추정하지 않는다.
-- =========================================================

CREATE VIEW team3_medallion.baek_silver_encounter_context AS
SELECT
    e.*,

    c.checkin_id AS matched_checkin_id,
    s.session_id AS matched_session_id,

    hd.hospital_department_id
        AS matched_hospital_department_id,

    h.hospital_id AS matched_hospital_id,
    d.department_code AS matched_department_code,

    h.hospital_name,
    d.department_name,

    CASE
        WHEN h.hospital_id IS NOT NULL
         AND REGEXP_LIKE(
            h.hospital_id,
            '^HOS_[0-9]{9}$',
            'c'
         )
        THEN h.hospital_id
        ELSE '__UNCLASSIFIED__'
    END AS hospital_group,

    COALESCE(
        d.department_code,
        '__UNCLASSIFIED__'
    ) AS department_group,

    COALESCE(
        DATE_FORMAT(e.started_at, '%Y-%m'),
        '__UNCLASSIFIED__'
    ) AS treatment_month,

    CASE
        WHEN c.checkin_id IS NULL
            THEN 'MISSING_CHECKIN'
        WHEN s.session_id IS NULL
            THEN 'MISSING_SESSION'
        WHEN hd.hospital_department_id IS NULL
            THEN 'MISSING_HOSPITAL_DEPARTMENT'
        WHEN h.hospital_id IS NULL
            THEN 'MISSING_HOSPITAL'
        WHEN d.department_code IS NULL
            THEN 'MISSING_DEPARTMENT'
        WHEN NOT REGEXP_LIKE(
            h.hospital_id,
            '^HOS_[0-9]{9}$',
            'c'
        )
            THEN 'INVALID_HOSPITAL_KEY'
        ELSE 'LINKED'
    END AS context_status

FROM team3_medallion.encounters AS e

LEFT JOIN team3_medallion.checkins AS c
    ON c.checkin_id = e.checkin_id

LEFT JOIN team3_medallion.clinic_sessions AS s
    ON s.session_id = c.session_id

LEFT JOIN team3_medallion.hospital_departments AS hd
    ON hd.hospital_department_id = s.hospital_department_id

LEFT JOIN team3_medallion.hospitals AS h
    ON h.hospital_id = hd.hospital_id

LEFT JOIN team3_medallion.departments AS d
    ON d.department_code = hd.department_code;


-- =========================================================
-- 7. 환불과 원결제 연결 검사
-- 여기서는 개별 환불을 검사한다.
-- 원결제별 누적 환불 한도는 후속 Gold에서 별도로 검사한다.
-- =========================================================

CREATE VIEW team3_medallion.baek_silver_refund_links AS
SELECT
    r.payment_id AS refund_id,
    r.encounter_id,
    r.transacted_at AS refunded_at,
    r.amount AS refund_amount,
    r.original_payment_id,

    p.payment_id AS matched_original_payment_id,
    p.payment_method AS original_payment_method,
    p.amount AS original_amount,
    p.transacted_at AS original_paid_at,

    CASE
        WHEN p.payment_id IS NULL
            THEN 'MISSING_ORIGINAL'

        WHEN p.transaction_type IS NULL
          OR CAST(p.transaction_type AS BINARY) <> 'PAYMENT'
            THEN 'ORIGINAL_NOT_PAYMENT'

        WHEN r.encounter_id IS NULL
          OR p.encounter_id IS NULL
          OR CAST(r.encounter_id AS BINARY)
                <> CAST(p.encounter_id AS BINARY)
            THEN 'DIFFERENT_OR_UNKNOWN_ENCOUNTER'

        WHEN r.transacted_at IS NULL
          OR p.transacted_at IS NULL
            THEN 'UNKNOWN_TIME'

        WHEN r.transacted_at <= p.transacted_at
            THEN 'REFUND_NOT_AFTER_PAYMENT'

        WHEN r.amount IS NULL
          OR p.amount IS NULL
          OR r.amount <= 0
          OR p.amount <= 0
          OR r.amount > p.amount
            THEN 'INVALID_AMOUNT'

        ELSE 'LINK_VALID'
    END AS link_status

FROM team3_medallion.payments AS r

LEFT JOIN team3_medallion.payments AS p
    ON p.payment_id = r.original_payment_id

WHERE CAST(r.transaction_type AS BINARY) = 'REFUND';


-- =========================================================
-- 8. 진단 조회
-- 아래 결과만으로 전체 정합성 통과를 선언하지 않는다.
-- =========================================================


-- 8-1. 정상 결제 테이블의 최종 진료 연결 현황
-- 연결 실패 행도 전체 거래 건수에 포함한다.

SELECT
    p.transaction_type,
    COUNT(*) AS transaction_rows,
    COUNT(e.encounter_id) AS linked_rows,

    SUM(
        CASE WHEN e.encounter_id IS NULL THEN 1 ELSE 0 END
    ) AS missing_final_encounter_rows

FROM team3_medallion.payments AS p

LEFT JOIN team3_medallion.encounters AS e
    ON e.encounter_id = p.encounter_id

GROUP BY p.transaction_type;


-- 8-2. 환불의 개별 원결제 연결 검사 결과

SELECT
    link_status,
    COUNT(*) AS refund_rows

FROM team3_medallion.baek_silver_refund_links

GROUP BY link_status;


-- 8-3. 격리 결제의 연결용 키 생성 가능 여부
-- LINKABLE_KEY_ONLY는 정상 판정이 아니다.

SELECT
    CASE
        WHEN linked_encounter_id IS NULL
            THEN 'UNLINKABLE'
        ELSE 'LINKABLE_KEY_ONLY'
    END AS key_status,

    COUNT(*) AS quarantine_rows

FROM team3_medallion.baek_silver_quarantine_payment_keys

GROUP BY key_status;


-- 8-4. 현재 정상·격리·제외 테이블의 행 수
-- 원본 수신행과의 대사에는 실제 입력 버전·실행 기록이 필요하다.

SELECT
    'normal' AS bucket,
    COUNT(*) AS rows_in_bucket
FROM team3_medallion.payments

UNION ALL

SELECT
    'quarantine',
    COUNT(*)
FROM team3_medallion_dq.payments_quarantine

UNION ALL

SELECT
    'excluded_retransmissions',
    COUNT(*)
FROM team3_medallion_dq.payments_excluded;