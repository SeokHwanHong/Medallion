-- MySQL 8.4. 먼저 02 실행. 새로운 baek_* VIEW만 생성; 정상/격리 데이터 수정 없음.
-- CREATE VIEW는 이름 충돌 시 실패한다. 기존 03/05/06 Spark SQL과 혼용 금지.
-- 모든 진료를 유지한다. 거래/서비스를 각각 진료별 집계한 뒤 연결하여 금액 증폭 방지.

-- 오토커밋 해제
SET SESSION autocommit = 0;

-- 읽기 전용 분석 시작 CTE, VIEW 위주 분석하기로.
START TRANSACTION WITH CONSISTENT SNAPSHOT, READ ONLY;

-- 분석 중 다른 세션이 데이터를 변경해도 같은 스냅샷으로 조회하고,
-- 현재 트랜잭션에서는 업무 데이터 변경을 제한.
START TRANSACTION WITH CONSISTENT SNAPSHOT, READ ONLY; 


CREATE VIEW team3_medallion.baek_gold_encounter_finance AS
SELECT e.*,
 COALESCE(p.transaction_rows,0) transaction_rows,
 COALESCE(p.payment_rows,0) payment_rows, COALESCE(p.refund_rows,0) refund_rows,
 COALESCE(p.paid_amount,0) paid_amount, COALESCE(p.refunded_amount,0) refunded_amount,
 COALESCE(p.paid_amount,0)-COALESCE(p.refunded_amount,0) recorded_net_amount,
 COALESCE(p.paid_amount,0)-COALESCE(p.refunded_amount,0)-e.net_charge transaction_gap,
 s.service_amount, s.service_amount-e.gross_charge service_gap,
 COALESCE(s.service_rows,0) service_rows,
 COALESCE(p.invalid_transaction_rows,0) invalid_transaction_rows,
 COALESCE(p.missing_transaction_time_rows,0) missing_transaction_time_rows,
 COALESCE(s.invalid_service_rows,0) invalid_service_rows,
 COALESCE(qp.quarantine_payment_rows,0) quarantine_payment_rows,
 COALESCE(qs.quarantine_service_rows,0) quarantine_service_rows,
 p.first_payment_at,p.last_payment_at,p.first_transaction_at,p.last_transaction_at,
 TIMESTAMPDIFF(MINUTE,e.ended_at,p.first_payment_at) first_payment_minutes_from_end,
 CASE WHEN p.method_count>1 THEN 'MIXED'
 WHEN p.method_count=1 THEN CONCAT('SINGLE_',p.single_method_candidate)
 ELSE 'NO_KNOWN_PAYMENT_METHOD' END AS method_bundle,
 CASE WHEN e.net_charge IS NULL OR e.gross_charge IS NULL OR e.authorized_refund IS NULL THEN 'UNKNOWN_CHARGE'
 WHEN e.net_charge<>e.gross_charge-e.authorized_refund OR e.authorized_refund<0 OR e.authorized_refund>e.gross_charge THEN 'INVALID_CHARGE'
 WHEN COALESCE(p.invalid_transaction_rows,0)>0 OR COALESCE(s.invalid_service_rows,0)>0 THEN 'INVALID_CHILD_VALUES'
 WHEN p.transaction_rows IS NULL THEN 'NO_RECORDED_TRANSACTION'
 WHEN qp.quarantine_payment_rows>0 OR qs.quarantine_service_rows>0 THEN 'LINKED_QUARANTINE_PRESENT'
 WHEN s.service_rows IS NULL THEN 'NO_RECORDED_SERVICE'
 WHEN p.paid_amount-p.refunded_amount<>e.net_charge OR s.service_amount<>e.gross_charge THEN 'DIFFERENCE_NO_LINKED_DQ'
 ELSE 'CURRENT_VALUES_MATCH_NO_LINKED_DQ' END AS evidence_status
FROM team3_medallion.baek_silver_encounter_context e
LEFT JOIN team3_medallion.baek_silver_payment_totals p ON p.encounter_id=e.encounter_id
LEFT JOIN team3_medallion.baek_silver_service_totals s ON s.encounter_id=e.encounter_id
LEFT JOIN team3_medallion.baek_silver_qpayment_totals qp ON qp.encounter_id=e.encounter_id
LEFT JOIN team3_medallion.baek_silver_qservice_totals qs ON qs.encounter_id=e.encounter_id;

-- 원결제당 1행. 환불 없는 원결제도 포함. 환불수단이 아닌 원결제수단에 귀속한다.
-- 여러 환불의 합계가 원결제를 초과하는지도 별도로 드러낸다.
-- 이 뷰는 전체 현재 기록 기준이다. 07의 환불률은 별도 관찰창 집계로 계산한다.
CREATE VIEW team3_medallion.baek_gold_original_payment_refunds AS
WITH refunds AS (
 SELECT original_payment_id,COUNT(*) linked_refund_rows,
 SUM(link_status='LINK_VALID') valid_link_rows,
 SUM(CASE WHEN link_status='LINK_VALID' THEN refund_amount ELSE 0 END) valid_link_refund_amount,
 SUM(link_status<>'LINK_VALID') invalid_link_rows,
 MIN(CASE WHEN link_status='LINK_VALID' THEN refunded_at END) first_valid_refund_at
 FROM team3_medallion.baek_silver_refund_links GROUP BY original_payment_id
), dq AS (
 SELECT linked_original_payment_id,COUNT(*) quarantine_reference_rows
 FROM team3_medallion.baek_silver_quarantine_payment_keys
 WHERE linked_original_payment_id IS NOT NULL GROUP BY linked_original_payment_id
)
SELECT p.payment_id,p.encounter_id,p.transacted_at,p.payment_method,p.source_system,p.amount,
 COALESCE(r.linked_refund_rows,0) linked_refund_rows,
 COALESCE(r.valid_link_rows,0) valid_link_rows,
 COALESCE(r.valid_link_refund_amount,0) valid_link_refund_amount,
 COALESCE(r.invalid_link_rows,0) invalid_link_rows,
 COALESCE(r.valid_link_refund_amount,0)>p.amount AS cumulative_refund_exceeds_original,
 COALESCE(dq.quarantine_reference_rows,0) quarantine_reference_rows,
 r.first_valid_refund_at,
 TIMESTAMPDIFF(MINUTE,p.transacted_at,r.first_valid_refund_at) minutes_to_first_refund,
 CASE WHEN e.encounter_id IS NULL THEN 'MISSING_FINAL_ENCOUNTER' ELSE 'LINKED' END AS encounter_link_status
FROM team3_medallion.payments p
LEFT JOIN refunds r ON r.original_payment_id=p.payment_id
LEFT JOIN dq ON dq.linked_original_payment_id=p.payment_id
LEFT JOIN team3_medallion.encounters e ON e.encounter_id=p.encounter_id
WHERE BINARY p.transaction_type='PAYMENT';

-- 소주제 전용: 진료 1건. 판단 보류와 관측 금액 일치 여부는 독립적으로 보존.
-- 진료 완료는 정상 encounters의 ended_at 존재 및 시간순서로만 판단한다.
-- 완료 상태 컬럼이 없으므로 임상적 완료를 별도로 입증하는 것은 아니다.
CREATE VIEW team3_medallion.baek_gold_collection_topic AS
WITH bad_refunds AS (
 SELECT encounter_id,COUNT(*) invalid_refund_links
 FROM team3_medallion.baek_silver_refund_links
 WHERE link_status<>'LINK_VALID' GROUP BY encounter_id
), excessive AS (
 SELECT encounter_id,COUNT(*) excessive_refund_originals
 FROM team3_medallion.baek_gold_original_payment_refunds
 WHERE cumulative_refund_exceeds_original=1 GROUP BY encounter_id
), timing AS (
 SELECT p.encounter_id,
 SUM(CASE WHEN BINARY p.transaction_type='PAYMENT' AND p.transacted_at>=e.ended_at THEN 1 ELSE 0 END) payments_at_or_after_end,
 SUM(CASE WHEN BINARY p.transaction_type='PAYMENT' AND p.transacted_at<e.ended_at THEN 1 ELSE 0 END) payments_before_end,
 SUM(CASE WHEN DATE(p.transacted_at)<>DATE(e.ended_at) THEN 1 ELSE 0 END) different_end_date_transactions
 FROM team3_medallion.payments p
 JOIN team3_medallion.encounters e ON e.encounter_id=p.encounter_id
 GROUP BY p.encounter_id
)
SELECT f.*,
 CASE WHEN f.started_at IS NOT NULL AND f.ended_at IS NOT NULL
 AND f.ended_at>=f.started_at AND f.ended_at<'2026-01-01' THEN 1 ELSE 0 END completed_in_observation,
 COALESCE(t.payments_at_or_after_end,0) payments_at_or_after_end,
 COALESCE(t.payments_before_end,0) payments_before_end,
 COALESCE(t.different_end_date_transactions,0) different_end_date_transactions,
 CASE WHEN f.started_at IS NULL OR f.ended_at IS NULL OR f.ended_at<f.started_at THEN 'HOLD_COMPLETION_UNKNOWN'
 WHEN f.ended_at>='2026-01-01' THEN 'OUTSIDE_OBSERVATION'
 WHEN f.net_charge IS NULL OR f.gross_charge IS NULL OR f.authorized_refund IS NULL
 OR f.gross_charge<0 OR f.authorized_refund<0 OR f.authorized_refund>f.gross_charge
 OR f.net_charge<>f.gross_charge-f.authorized_refund THEN 'HOLD_CHARGE_INVALID'
 WHEN f.invalid_transaction_rows>0 OR f.missing_transaction_time_rows>0 THEN 'HOLD_TRANSACTION_INVALID'
 WHEN f.quarantine_payment_rows>0 OR f.quarantine_service_rows>0 THEN 'HOLD_LINKED_QUARANTINE'
 WHEN COALESCE(r.invalid_refund_links,0)>0 OR COALESCE(x.excessive_refund_originals,0)>0 THEN 'HOLD_REFUND_LINK_OR_TOTAL'
 WHEN f.invalid_service_rows>0 OR f.service_rows=0 THEN 'HOLD_SERVICE_EVIDENCE'
 WHEN f.last_transaction_at>='2026-01-01' THEN 'HOLD_AFTER_OBSERVATION'
 ELSE 'ASSESSABLE_CURRENT_LINKED_RECORDS' END AS judgement_status
FROM team3_medallion.baek_gold_encounter_finance f
LEFT JOIN bad_refunds r ON r.encounter_id=f.encounter_id
LEFT JOIN excessive x ON x.encounter_id=f.encounter_id
LEFT JOIN timing t ON t.encounter_id=f.encounter_id;
