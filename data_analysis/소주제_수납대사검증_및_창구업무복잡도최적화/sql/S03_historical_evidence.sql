-- 목적: 수정본 생성 당시 대사 근거별 확인 대상은?
-- 입력: 로컬 캐시 및 수정 합성자료; 출력: S03_historical_evidence 결과
-- 질문: 수정본 생성 당시 대사 근거별 확인 대상은?
-- 한 행의 의미: BASE 대사 판정별 1행
-- 모집단·분모: BASE RECONCILE 작업만; CHECK 미판정은 보류로 세지 않음
-- 결과 해석: 과거 로컬 입력 기준으로 현재 최종 DB 판정과 다름
-- 소주제와 연결: 금액 차이와 근거 부족을 다른 경로로 점검
-- 실행: SQLite 로컬 메모리. MySQL 8 호환 SELECT 구문이나 현재 MySQL 실행 미검증.
-- final_*는 로컬 캐시 별칭이며 실제 DB 테이블명이 아님. DB 생성·적재 지시가 아님.
SELECT reconciliation_result,COUNT(*) payment_count,SUM(work_minutes) reconcile_task_minutes,
100.0*COUNT(*)/(SELECT COUNT(*) FROM ext_collection_worklogs WHERE scenario_id='BASE' AND task_type='RECONCILE') percent
FROM ext_collection_worklogs WHERE scenario_id='BASE' AND task_type='RECONCILE'
GROUP BY reconciliation_result;
