-- 목적: 최종 병원별 분할결제·환불의 합산 확인 규모는?
-- 입력: 로컬 캐시 및 수정 합성자료; 출력: S08_final_hospital 결과
-- 질문: 최종 병원별 분할결제·환불의 합산 확인 규모는?
-- 한 행의 의미: 병원별 1행
-- 모집단·분모: 해당 병원 완료 진료 전체
-- 결과 해석: 건수는 처리 규모; 비율 차이가 작으면 성과 우열로 표현하지 않음
-- 소주제와 연결: 점검 우선순위는 오류 발생 순위가 아니라 합산 확인 규모
-- 실행: SQLite 로컬 메모리. MySQL 8 호환 SELECT 구문이나 현재 MySQL 실행 미검증.
-- final_*는 로컬 캐시 별칭이며 실제 DB 테이블명이 아님. DB 생성·적재 지시가 아님.
SELECT hospital_id,hospital_name,COUNT(*) encounters,
SUM(CASE WHEN payment_count>=2 THEN 1 ELSE 0 END) split_count,
100.0*SUM(CASE WHEN payment_count>=2 THEN 1 ELSE 0 END)/COUNT(*) split_percent,
SUM(CASE WHEN refund_count>0 THEN 1 ELSE 0 END) refund_count,
100.0*SUM(CASE WHEN refund_count>0 THEN 1 ELSE 0 END)/COUNT(*) refund_percent,
SUM(CASE WHEN hold=0 AND gap<>0 THEN 1 ELSE 0 END) difference_count,SUM(hold) hold_count
FROM final_encounters WHERE completed=1 GROUP BY hospital_id,hospital_name ORDER BY split_count DESC;
