-- [백선영] 목적: 수정본 결제가 최종 캐시에 얼마나 남아 있는가?
-- 입력: 로컬 캐시 및 수정 합성자료; 출력: S04_final_link_coverage 결과
-- 질문: 수정본 결제가 최종 캐시에 얼마나 남아 있는가?
-- 한 행의 의미: 과거 판정×최종 키 연결 여부
-- 모집단·분모: BASE RECONCILE 1749건; payment_id와 encounter_id 동시 일치
-- 결과 해석: 키 일치가 옛 판정의 현재 유효성을 뜻하지 않음; 미연결 원인은 확정 불가
-- 소주제와 연결: 서로 다른 기준의 자료 혼합 방지
-- 실행: SQLite 로컬 메모리. MySQL 8 호환 SELECT 구문이나 현재 MySQL 실행 미검증.
-- final_*는 로컬 캐시 별칭이며 실제 DB 테이블명이 아님. DB 생성·적재 지시가 아님.
SELECT w.reconciliation_result,
CASE WHEN p.payment_id IS NULL THEN 'NOT_LINKED' ELSE 'LINKED' END linkage,
COUNT(*) payments
FROM ext_collection_worklogs w LEFT JOIN final_payments p
ON w.payment_id=p.payment_id AND w.encounter_id=p.encounter_id
WHERE w.scenario_id='BASE' AND w.task_type='RECONCILE'
GROUP BY w.reconciliation_result,CASE WHEN p.payment_id IS NULL THEN 'NOT_LINKED' ELSE 'LINKED' END;
