-- 소주제: 진료 후 결제·환불 패턴 분석을 통한 병원 재정 관리 및 수납 업무 효율화 방향
-- 1행=진료 1건. 02->04 뷰 생성 후 실행. 뷰 생성 없는 실행판은 10 파일.
-- 관찰 종료: 2025-12-31 한국시간. 진료월=started_at 월, 거래월과 구별.
-- 미연결 격리 거래는 진료에 추정 배정할 수 없다. ASSESSABLE은 전체 무오류 보증 아님.
-- 환불률은 환불 발생 진료 수/비교 가능 완료 진료 수. 원결제 환불률(I07)과 다르다.
START TRANSACTION WITH CONSISTENT SNAPSHOT, READ ONLY;

-- T01 대상 범위: 미완료/완료판단불가를 분모에서 조용히 없애지 않는다.
SELECT completed_in_observation,judgement_status,COUNT(*) encounters
FROM team3_medallion.baek_gold_collection_topic
GROUP BY completed_in_observation,judgement_status;

-- T02 핵심 퍼널. 전체 완료 진료 분모와 비교 가능한 진료 분모를 모두 제공.
-- 3단계는 2단계의 부분집합. 환불만 있는 진료는 결제 발생으로 세지 않는다.
-- '같은 날'과 '종료 이후'는 다르므로 종료 전 결제는 별도 공개한다.
SELECT COUNT(*) completed_encounters,
 SUM(judgement_status<>'ASSESSABLE_CURRENT_LINKED_RECORDS') hold_encounters,
 SUM(judgement_status='ASSESSABLE_CURRENT_LINKED_RECORDS') assessable_encounters,
 SUM(payment_rows>0) observed_payment_encounters_including_hold,
 SUM(judgement_status='ASSESSABLE_CURRENT_LINKED_RECORDS' AND payment_rows>0) stage2_assessable_payment,
 SUM(judgement_status='ASSESSABLE_CURRENT_LINKED_RECORDS' AND payment_rows>0 AND transaction_gap=0) stage3_assessable_match,
 ROUND(100.0*SUM(judgement_status<>'ASSESSABLE_CURRENT_LINKED_RECORDS')/NULLIF(COUNT(*),0),3) hold_pct_of_completed,
 ROUND(100.0*SUM(judgement_status='ASSESSABLE_CURRENT_LINKED_RECORDS' AND payment_rows>0)/NULLIF(COUNT(*),0),3) stage2_pct_of_completed,
 ROUND(100.0*SUM(judgement_status='ASSESSABLE_CURRENT_LINKED_RECORDS' AND payment_rows>0 AND transaction_gap=0)/NULLIF(COUNT(*),0),3) stage3_pct_of_completed,
 ROUND(100.0*SUM(judgement_status='ASSESSABLE_CURRENT_LINKED_RECORDS' AND payment_rows>0 AND transaction_gap=0)
 /NULLIF(SUM(judgement_status='ASSESSABLE_CURRENT_LINKED_RECORDS' AND payment_rows>0),0),3) stage3_pct_of_stage2,
 SUM(payments_before_end>0) with_before_end_payment,
 SUM(payments_at_or_after_end>0) with_at_or_after_end_payment,
 SUM(different_end_date_transactions>0) with_different_date_transaction
FROM team3_medallion.baek_gold_collection_topic WHERE completed_in_observation=1;

-- T03 진료 발생 월별 코호트. 장기 회수율 아님. 보류 제외로 일치율이 높아지는지 같이 확인.
-- 차액=결제합-환불합-net_charge. 양/음 차액 상쇄 방지를 위해 절대차액도 제공.
-- 보류 차액은 관측치일 뿐 확정 불일치/손실로 표현하지 않는다.
SELECT treatment_month,COUNT(*) completed_encounters,
 SUM(judgement_status<>'ASSESSABLE_CURRENT_LINKED_RECORDS') hold_encounters,
 SUM(judgement_status='ASSESSABLE_CURRENT_LINKED_RECORDS') assessable_encounters,
 SUM(transaction_gap=0) observed_matches_including_hold,
 SUM(CASE WHEN judgement_status='ASSESSABLE_CURRENT_LINKED_RECORDS' THEN transaction_gap=0 ELSE 0 END) assessable_matches,
 ROUND(100.0*SUM(CASE WHEN judgement_status='ASSESSABLE_CURRENT_LINKED_RECORDS' THEN transaction_gap=0 ELSE 0 END)
 /NULLIF(SUM(judgement_status='ASSESSABLE_CURRENT_LINKED_RECORDS'),0),3) match_pct_of_assessable,
 ROUND(100.0*SUM(CASE WHEN judgement_status='ASSESSABLE_CURRENT_LINKED_RECORDS' THEN transaction_gap=0 ELSE 0 END)
 /NULLIF(COUNT(*),0),3) confirmed_record_match_pct_of_all,
 SUM(transaction_gap) observed_signed_gap_all,
 SUM(CASE WHEN judgement_status='ASSESSABLE_CURRENT_LINKED_RECORDS' THEN transaction_gap END) assessable_signed_gap,
 SUM(CASE WHEN judgement_status='ASSESSABLE_CURRENT_LINKED_RECORDS' THEN ABS(transaction_gap) END) assessable_absolute_gap,
 SUM(CASE WHEN judgement_status='ASSESSABLE_CURRENT_LINKED_RECORDS' THEN net_charge END) assessable_net_charge,
 SUM(refund_rows>0) observed_refund_encounters_including_hold,
 ROUND(100.0*SUM(judgement_status='ASSESSABLE_CURRENT_LINKED_RECORDS' AND refund_rows>0)
 /NULLIF(SUM(judgement_status='ASSESSABLE_CURRENT_LINKED_RECORDS'),0),3) refund_pct_of_assessable
FROM team3_medallion.baek_gold_collection_topic
WHERE completed_in_observation=1 GROUP BY treatment_month ORDER BY treatment_month;

-- T04 점검 구간: 병원/진료과/원천별 보류·불일치 분리. 비교 불가능한 집단도 보존.
SELECT treatment_month,source_system,hospital_group,department_group,judgement_status,
 COUNT(*) encounters,SUM(payment_rows=0) without_payment_record,
 SUM(transaction_gap<>0) observed_gap_encounters,
 SUM(quarantine_payment_rows>0) linked_payment_quarantine,
 SUM(quarantine_service_rows>0) linked_service_quarantine,
 SUM(context_status<>'LINKED') dimension_unclassified
FROM team3_medallion.baek_gold_collection_topic WHERE completed_in_observation=1
GROUP BY treatment_month,source_system,hospital_group,department_group,judgement_status;
ROLLBACK;
