-- 06. 원천 비교 마무리 (조회 전용)
SET SESSION TRANSACTION READ ONLY;
SET SESSION sql_big_selects = 1;
USE team3_medallion;

SELECT '## S13 병원별 매출 순위: 원 매출 vs 수량 표준화(단가 합) 매출' AS section;
WITH es AS (SELECT encounter_id, SUM(unit_price) unit_sum FROM encounter_services GROUP BY encounter_id),
     hosp AS (SELECT h.hospital_id, COUNT(*) enc, SUM(e.gross_charge) rev, SUM(es.unit_sum) rev_std
              FROM encounters e JOIN es ON es.encounter_id = e.encounter_id JOIN checkins c ON c.checkin_id = e.checkin_id
              JOIN clinic_sessions s ON s.session_id = c.session_id JOIN hospital_departments h ON h.hospital_department_id = s.hospital_department_id
              GROUP BY h.hospital_id),
     rk AS (SELECT hosp.*, CAST(RANK() OVER (ORDER BY rev DESC) AS SIGNED) rk_raw, CAST(RANK() OVER (ORDER BY rev_std DESC) AS SIGNED) rk_std,
                   CAST(RANK() OVER (ORDER BY enc DESC) AS SIGNED) rk_enc FROM hosp)
SELECT COUNT(*) hospitals, ROUND(AVG(ABS(rk_raw - rk_std)), 1) avg_rank_shift, MAX(ABS(rk_raw - rk_std)) max_rank_shift,
       SUM(ABS(rk_raw - rk_std) >= 50) shift_50plus, SUM(rk_raw <= 50 AND rk_std > 50) top50_dropped,
       ROUND(AVG(ABS(rk_raw - rk_enc)), 1) avg_shift_vs_volume_rank, ROUND(AVG(ABS(rk_std - rk_enc)), 1) avg_shift_std_vs_volume_rank
FROM rk;

SELECT '## S14 병원 원천별 병원당 진료·원 매출·표준화 매출' AS section;
WITH es AS (SELECT encounter_id, SUM(unit_price) unit_sum FROM encounter_services GROUP BY encounter_id),
     hosp AS (SELECT h.hospital_id, COUNT(*) enc, SUM(e.gross_charge) rev, SUM(es.unit_sum) rev_std
              FROM encounters e JOIN es ON es.encounter_id = e.encounter_id JOIN checkins c ON c.checkin_id = e.checkin_id
              JOIN clinic_sessions s ON s.session_id = c.session_id JOIN hospital_departments h ON h.hospital_department_id = s.hospital_department_id
              GROUP BY h.hospital_id)
SELECT hp.source_system hosp_src, COUNT(*) hospitals, ROUND(AVG(enc)) avg_enc, ROUND(AVG(rev)) avg_rev, ROUND(AVG(rev_std)) avg_rev_std
FROM hosp JOIN hospitals hp ON hp.hospital_id = hosp.hospital_id GROUP BY hp.source_system;

SELECT '## S15 환자 원천 x 예약 원천: 환자 단위 교차 이용' AS section;
WITH p AS (SELECT a.patient_id, MAX(a.source_system = 'LEGACY_A') use_a, MAX(a.source_system = 'LEGACY_B') use_b FROM appointments a GROUP BY a.patient_id)
SELECT pt.source_system patient_src, SUM(use_a AND NOT use_b) only_a, SUM(use_b AND NOT use_a) only_b, SUM(use_a AND use_b) both_ab, COUNT(*) patients
FROM p JOIN patients pt ON pt.patient_id = p.patient_id GROUP BY pt.source_system;

SELECT '## S16 접수의 환자 원천 x 접수 원천' AS section;
SELECT c.source_system checkin_src, pt.source_system patient_src, COUNT(*) n FROM checkins c JOIN patients pt ON pt.patient_id = c.patient_id GROUP BY c.source_system, pt.source_system;

SELECT '## S17 원천별 상위 10% 병원(원 매출) 구성' AS section;
WITH hosp AS (SELECT h.hospital_id, SUM(e.gross_charge) rev FROM encounters e JOIN checkins c ON c.checkin_id = e.checkin_id
              JOIN clinic_sessions s ON s.session_id = c.session_id JOIN hospital_departments h ON h.hospital_department_id = s.hospital_department_id GROUP BY h.hospital_id),
     k AS (SELECT hosp.*, NTILE(10) OVER (ORDER BY rev DESC) d10 FROM hosp)
SELECT d10, hp.source_system, COUNT(*) hospitals FROM k JOIN hospitals hp ON hp.hospital_id = k.hospital_id GROUP BY d10, hp.source_system ORDER BY d10, hp.source_system;
