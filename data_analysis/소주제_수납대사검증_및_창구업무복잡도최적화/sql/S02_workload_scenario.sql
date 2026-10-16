-- 목적: 수납 확인 절차의 복잡화 가정에 따라 작업량은 어떻게 변하는가?
-- 입력: 로컬 캐시 및 수정 합성자료; 출력: S02_workload_scenario 결과
-- 질문: 수납 확인 절차의 복잡화 가정에 따라 작업량은 어떻게 변하는가?
-- 한 행의 의미: 시나리오별 작업 유형
-- 모집단·분모: 시나리오마다 같은 결제 1749건; 시나리오 합산 금지
-- 결과 해석: 생성된 task-minutes이며 실제 노동시간이나 대기시간 아님
-- 소주제와 연결: 재확인 절차 설계의 민감도
-- 실행: SQLite 로컬 메모리. MySQL 8 호환 SELECT 구문이나 현재 MySQL 실행 미검증.
-- final_*는 로컬 캐시 별칭이며 실제 DB 테이블명이 아님. DB 생성·적재 지시가 아님.
SELECT scenario_id, task_type, COUNT(*) tasks, COUNT(DISTINCT payment_id) payments,
SUM(work_minutes) task_minutes, AVG(work_minutes) minutes_per_task
FROM ext_collection_worklogs WHERE scenario_id IN ('BASE','COLLECTION_COMPLEX')
GROUP BY scenario_id,task_type ORDER BY scenario_id,task_type;
