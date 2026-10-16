-- [백선영] 목적: 최종 기록에서 차이와 합산 확인 규모는?
-- 입력: 로컬 캐시 및 수정 합성자료; 출력: S01_final_finance 결과
-- 질문: 최종 기록에서 차이와 합산 확인 규모는?
-- 한 행의 의미: 전체 완료 진료 1행
-- 모집단·분모: 완료 진료; 비교 가능 집단은 hold=0
-- 결과 해석: 차이는 실제 미수금이 아니며 0이면 그대로 공개
-- 소주제와 연결: 기존 재정 대사 결과를 보존
-- 실행: SQLite 로컬 메모리. MySQL 8 호환 SELECT 구문이나 현재 MySQL 실행 미검증.
-- final_*는 로컬 캐시 별칭이며 실제 DB 테이블명이 아님. DB 생성·적재 지시가 아님.
SELECT COUNT(*) encounters, SUM(CASE WHEN hold=0 THEN 1 ELSE 0 END) assessable,
SUM(CASE WHEN hold=0 AND gap=0 THEN 1 ELSE 0 END) matched,
SUM(CASE WHEN hold=0 AND gap<>0 THEN 1 ELSE 0 END) difference,
SUM(CASE WHEN payment_count=0 THEN 1 ELSE 0 END) missing_payment,
SUM(hold) hold_count, SUM(CASE WHEN payment_count>=2 THEN 1 ELSE 0 END) split_count,
SUM(CASE WHEN refund_count>0 THEN 1 ELSE 0 END) refund_count,
SUM(paid) paid, SUM(refunded) refunded, SUM(recorded_net) recorded_net,
SUM(CASE WHEN hold=0 THEN ABS(gap) ELSE 0 END) absolute_gap
FROM final_encounters WHERE completed=1;
