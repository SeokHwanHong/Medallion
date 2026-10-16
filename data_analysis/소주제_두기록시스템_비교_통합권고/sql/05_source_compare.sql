-- 05. 원천(LEGACY_A/B) 비교 (조회 전용: SELECT 만 사용)
SET SESSION TRANSACTION READ ONLY;
SET SESSION sql_big_selects = 1;
USE team3_medallion;

SELECT '## S01 Silver 원천별 행 수' AS section;
SELECT 'hospitals' t, source_system src, COUNT(*) n FROM hospitals GROUP BY source_system
UNION ALL SELECT 'hospital_departments', source_system, COUNT(*) FROM hospital_departments GROUP BY source_system
UNION ALL SELECT 'doctors', source_system, COUNT(*) FROM doctors GROUP BY source_system
UNION ALL SELECT 'doctor_assignments', source_system, COUNT(*) FROM doctor_assignments GROUP BY source_system
UNION ALL SELECT 'patients', source_system, COUNT(*) FROM patients GROUP BY source_system
UNION ALL SELECT 'clinic_sessions', source_system, COUNT(*) FROM clinic_sessions GROUP BY source_system
UNION ALL SELECT 'appointment_slots', source_system, COUNT(*) FROM appointment_slots GROUP BY source_system
UNION ALL SELECT 'appointments', source_system, COUNT(*) FROM appointments GROUP BY source_system
UNION ALL SELECT 'appointment_events', source_system, COUNT(*) FROM appointment_events GROUP BY source_system
UNION ALL SELECT 'checkins', source_system, COUNT(*) FROM checkins GROUP BY source_system
UNION ALL SELECT 'encounters', source_system, COUNT(*) FROM encounters GROUP BY source_system
UNION ALL SELECT 'encounter_services', source_system, COUNT(*) FROM encounter_services GROUP BY source_system
UNION ALL SELECT 'payments', source_system, COUNT(*) FROM payments GROUP BY source_system;

SELECT '## S02 부모-자식 원천 일치 (한 업무 흐름이 두 시스템에 걸쳐 있는가)' AS section;
SELECT 'checkins->clinic_sessions' rel, c.source_system child_src, p.source_system parent_src, COUNT(*) n FROM checkins c JOIN clinic_sessions p ON p.session_id = c.session_id GROUP BY c.source_system, p.source_system
UNION ALL SELECT 'encounters->checkins', c.source_system, p.source_system, COUNT(*) FROM encounters c JOIN checkins p ON p.checkin_id = c.checkin_id GROUP BY c.source_system, p.source_system
UNION ALL SELECT 'encounter_services->encounters', c.source_system, p.source_system, COUNT(*) FROM encounter_services c JOIN encounters p ON p.encounter_id = c.encounter_id GROUP BY c.source_system, p.source_system
UNION ALL SELECT 'payments->encounters', c.source_system, p.source_system, COUNT(*) FROM payments c JOIN encounters p ON p.encounter_id = c.encounter_id GROUP BY c.source_system, p.source_system
UNION ALL SELECT 'appointments->appointment_slots', c.source_system, p.source_system, COUNT(*) FROM appointments c JOIN appointment_slots p ON p.slot_id = c.slot_id GROUP BY c.source_system, p.source_system
UNION ALL SELECT 'appointments->patients', c.source_system, p.source_system, COUNT(*) FROM appointments c JOIN patients p ON p.patient_id = c.patient_id GROUP BY c.source_system, p.source_system
UNION ALL SELECT 'appointment_slots->clinic_sessions', c.source_system, p.source_system, COUNT(*) FROM appointment_slots c JOIN clinic_sessions p ON p.session_id = c.session_id GROUP BY c.source_system, p.source_system
UNION ALL SELECT 'clinic_sessions->hospital_departments', c.source_system, p.source_system, COUNT(*) FROM clinic_sessions c JOIN hospital_departments p ON p.hospital_department_id = c.hospital_department_id GROUP BY c.source_system, p.source_system
UNION ALL SELECT 'hospital_departments->hospitals', c.source_system, p.source_system, COUNT(*) FROM hospital_departments c JOIN hospitals p ON p.hospital_id = c.hospital_id GROUP BY c.source_system, p.source_system
UNION ALL SELECT 'doctor_assignments->doctors', c.source_system, p.source_system, COUNT(*) FROM doctor_assignments c JOIN doctors p ON p.doctor_id = c.doctor_id GROUP BY c.source_system, p.source_system;

SELECT '## S03 진료 1건의 전체 흐름(병원-세션-접수-진료-결제) 원천 일관성' AS section;
WITH f AS (
  SELECT e.encounter_id, hp.source_system s_h, s.source_system s_s, c.source_system s_c, e.source_system s_e
  FROM encounters e JOIN checkins c ON c.checkin_id = e.checkin_id JOIN clinic_sessions s ON s.session_id = c.session_id
  JOIN hospital_departments h ON h.hospital_department_id = s.hospital_department_id JOIN hospitals hp ON hp.hospital_id = h.hospital_id)
SELECT (s_h = s_s AND s_s = s_c AND s_c = s_e) all_same, COUNT(*) n FROM f GROUP BY all_same;

SELECT '## S04 병원별 진료의 B 원천 비중 분포' AS section;
WITH f AS (
  SELECT h.hospital_id, AVG(e.source_system = 'LEGACY_B') b_share FROM encounters e JOIN checkins c ON c.checkin_id = e.checkin_id
  JOIN clinic_sessions s ON s.session_id = c.session_id JOIN hospital_departments h ON h.hospital_department_id = s.hospital_department_id GROUP BY h.hospital_id)
SELECT FLOOR(b_share * 10) / 10 b_share_bucket, COUNT(*) hospitals FROM f GROUP BY b_share_bucket ORDER BY b_share_bucket;

SELECT '## S05 진료 원천별 업무 값 비교' AS section;
SELECT e.source_system src, COUNT(*) encounters, ROUND(AVG(e.gross_charge)) avg_gross, ROUND(AVG(e.authorized_refund)) avg_refund,
       ROUND(AVG(e.authorized_refund > 0) * 100, 2) refund_enc_pct, ROUND(AVG(TIMESTAMPDIFF(MINUTE, e.started_at, e.ended_at)), 2) avg_minutes
FROM encounters e GROUP BY e.source_system;

SELECT '## S06 서비스 라인 원천별 수량·단가' AS section;
SELECT source_system src, COUNT(*) n_rows, ROUND(AVG(quantity), 3) avg_qty, ROUND(AVG(unit_price)) avg_unit, ROUND(AVG(line_amount)) avg_amount,
       SUM(line_amount <> quantity * unit_price) amount_formula_mismatch FROM encounter_services GROUP BY source_system;

SELECT '## S07 서비스 라인 번호별 수량 (원천별)' AS section;
SELECT source_system src, line_no, ROUND(AVG(quantity), 3) avg_qty, COUNT(*) n FROM encounter_services GROUP BY source_system, line_no ORDER BY src, line_no;

SELECT '## S08 결제 원천별 거래 유형·수단' AS section;
SELECT source_system src, transaction_type, payment_method, COUNT(*) n, ROUND(AVG(amount)) avg_amount FROM payments GROUP BY source_system, transaction_type, payment_method ORDER BY src, transaction_type, payment_method;

SELECT '## S09 접수 원천별 접수유형·결과' AS section;
SELECT source_system src, visit_type, outcome, COUNT(*) n FROM checkins GROUP BY source_system, visit_type, outcome ORDER BY src, visit_type, outcome;

SELECT '## S10 예약 원천별 상태·채널' AS section;
SELECT source_system src, status, channel, COUNT(*) n FROM appointments GROUP BY source_system, status, channel ORDER BY src, status, channel;

SELECT '## S11 환자 원천별 성별' AS section;
SELECT source_system src, sex_code, COUNT(*) n FROM patients GROUP BY source_system, sex_code ORDER BY src, sex_code;

SELECT '## S12 진료 원천 x 병원 원천별 진료당 청구' AS section;
SELECT hp.source_system hosp_src, e.source_system enc_src, COUNT(*) n, ROUND(AVG(e.gross_charge)) avg_gross
FROM encounters e JOIN checkins c ON c.checkin_id = e.checkin_id JOIN clinic_sessions s ON s.session_id = c.session_id
JOIN hospital_departments h ON h.hospital_department_id = s.hospital_department_id JOIN hospitals hp ON hp.hospital_id = h.hospital_id
GROUP BY hp.source_system, e.source_system;

SELECT '## S13 병원별 매출 순위: 원 매출 vs 수량 표준화(단가 합) 매출' AS section;
WITH es AS (SELECT encounter_id, SUM(unit_price) unit_sum FROM encounter_services GROUP BY encounter_id),
     hosp AS (SELECT h.hospital_id, COUNT(*) enc, SUM(e.gross_charge) rev, SUM(es.unit_sum) rev_std
              FROM encounters e JOIN es ON es.encounter_id = e.encounter_id JOIN checkins c ON c.checkin_id = e.checkin_id
              JOIN clinic_sessions s ON s.session_id = c.session_id JOIN hospital_departments h ON h.hospital_department_id = s.hospital_department_id
              GROUP BY h.hospital_id),
     rk AS (SELECT hosp.*, RANK() OVER (ORDER BY rev DESC) rk_raw, RANK() OVER (ORDER BY rev_std DESC) rk_std,
                   RANK() OVER (ORDER BY enc DESC) rk_enc FROM hosp)
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
