-- 목적: 서비스 업무량 가정은 무엇을 비교할 수 있는가?
-- 입력: 로컬 캐시 및 수정 합성자료; 출력: S07_service_proxy 결과
-- 질문: 서비스 업무량 가정은 무엇을 비교할 수 있는가?
-- 한 행의 의미: 서비스 코드×시나리오
-- 모집단·분모: 가격 버전별 값을 먼저 코드 단위 평균; 병원 총량으로 합산하지 않음
-- 결과 해석: 진료시간 배분 기반 대용값; 실측 서비스 시간·난이도 아님
-- 소주제와 연결: 확장 민감도 주제; 25% 증가는 설계값
-- 실행: SQLite 로컬 메모리. MySQL 8 호환 SELECT 구문이나 현재 MySQL 실행 미검증.
-- final_*는 로컬 캐시 별칭이며 실제 DB 테이블명이 아님. DB 생성·적재 지시가 아님.
SELECT scenario_id,service_code,COUNT(*) price_versions,
AVG(assumed_standard_minutes) proxy_minutes,AVG(assumed_workload_weight) proxy_weight
FROM ext_service_workload WHERE scenario_id IN ('BASE','WORKLOAD_UP')
GROUP BY scenario_id,service_code;
