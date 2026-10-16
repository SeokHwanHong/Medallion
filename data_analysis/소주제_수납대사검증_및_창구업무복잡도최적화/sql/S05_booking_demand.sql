-- 목적: 추가 예약 수요 가정에서 제안가능 비율과 대기 발생은?
-- 입력: 로컬 캐시 및 수정 합성자료; 출력: S05_booking_demand 결과
-- 질문: 추가 예약 수요 가정에서 제안가능 비율과 대기 발생은?
-- 한 행의 의미: 시나리오×요청 판단
-- 모집단·분모: 활성 요청만; WITHDRAWN도 활성 분모에 포함; 비활성 비교행 제외
-- 결과 해석: OFFERABLE은 가정상 제안가능이며 예약 확정 아님
-- 소주제와 연결: 확장 주제: 수요 대응 절차; 재정 차이 원인으로 연결하지 않음
-- 실행: SQLite 로컬 메모리. MySQL 8 호환 SELECT 구문이나 현재 MySQL 실행 미검증.
-- final_*는 로컬 캐시 별칭이며 실제 DB 테이블명이 아님. DB 생성·적재 지시가 아님.
WITH a AS (SELECT * FROM ext_booking_requests WHERE is_active='Y' AND scenario_id IN ('BASE','DEMAND_UP')),
d AS (SELECT scenario_id,COUNT(*) denominator FROM a GROUP BY scenario_id)
SELECT a.scenario_id,a.decision,COUNT(*) requests,d.denominator,
100.0*COUNT(*)/d.denominator percent FROM a JOIN d ON a.scenario_id=d.scenario_id
GROUP BY a.scenario_id,a.decision,d.denominator;
