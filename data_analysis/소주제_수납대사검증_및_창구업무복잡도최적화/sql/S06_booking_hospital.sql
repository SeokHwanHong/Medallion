-- 목적: 병원별 추가 요청의 제안가능 비율은?
-- 입력: 로컬 캐시 및 수정 합성자료; 출력: S06_booking_hospital 결과
-- 질문: 병원별 추가 요청의 제안가능 비율은?
-- 한 행의 의미: 시나리오×병원
-- 모집단·분모: 각 병원의 활성 요청
-- 결과 해석: 표본 12개 병원; 수요 증가 가정이며 실제 병원 병목 증거 아님
-- 소주제와 연결: 규모와 비율을 함께 비교하는 확장 분석
-- 실행: SQLite 로컬 메모리. MySQL 8 호환 SELECT 구문이나 현재 MySQL 실행 미검증.
-- final_*는 로컬 캐시 별칭이며 실제 DB 테이블명이 아님. DB 생성·적재 지시가 아님.
SELECT scenario_id,hospital_id,COUNT(*) active_requests,
SUM(CASE WHEN decision='OFFERABLE' THEN 1 ELSE 0 END) offerable,
SUM(CASE WHEN decision='WAITLIST' THEN 1 ELSE 0 END) waitlist,
100.0*SUM(CASE WHEN decision='OFFERABLE' THEN 1 ELSE 0 END)/COUNT(*) offerable_percent
FROM ext_booking_requests WHERE is_active='Y' AND scenario_id IN ('BASE','DEMAND_UP')
GROUP BY scenario_id,hospital_id;
