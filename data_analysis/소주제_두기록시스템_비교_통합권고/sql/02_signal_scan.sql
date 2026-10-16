-- 02. 신호 탐색 (조회 전용: SELECT 만 사용)
SET SESSION TRANSACTION READ ONLY;
SET SESSION sql_big_selects = 1;
USE team3_medallion;

SELECT '## Q01 테이블 정확 건수' AS section;
SELECT 'hospitals' t, COUNT(*) n FROM hospitals UNION ALL SELECT 'departments', COUNT(*) FROM departments
UNION ALL SELECT 'hospital_departments', COUNT(*) FROM hospital_departments UNION ALL SELECT 'doctors', COUNT(*) FROM doctors
UNION ALL SELECT 'doctor_assignments', COUNT(*) FROM doctor_assignments UNION ALL SELECT 'patients', COUNT(*) FROM patients
UNION ALL SELECT 'clinic_sessions', COUNT(*) FROM clinic_sessions UNION ALL SELECT 'appointment_slots', COUNT(*) FROM appointment_slots
UNION ALL SELECT 'appointments', COUNT(*) FROM appointments UNION ALL SELECT 'appointment_events', COUNT(*) FROM appointment_events
UNION ALL SELECT 'checkins', COUNT(*) FROM checkins UNION ALL SELECT 'encounters', COUNT(*) FROM encounters
UNION ALL SELECT 'encounter_services', COUNT(*) FROM encounter_services UNION ALL SELECT 'service_catalog', COUNT(*) FROM service_catalog
UNION ALL SELECT 'payments', COUNT(*) FROM payments;

SELECT '## Q02 서비스 카탈로그: 분류별 서비스 수·단가' AS section;
SELECT service_category, COUNT(*) versions, COUNT(DISTINCT service_code) services, MIN(unit_price) min_p, ROUND(AVG(unit_price)) avg_p, MAX(unit_price) max_p
FROM service_catalog GROUP BY service_category ORDER BY service_category;

SELECT '## Q03 카탈로그 버전(유효기간 시작 연도)별 평균 단가' AS section;
SELECT service_category, YEAR(valid_from) y, COUNT(*) n, ROUND(AVG(unit_price)) avg_p FROM service_catalog GROUP BY service_category, YEAR(valid_from) ORDER BY service_category, y;

SELECT '## Q04 서비스별 단가 인상률 분포 (최초 버전 대비 최종 버전)' AS section;
WITH p AS (SELECT service_code, service_category, MIN(unit_price) p0, MAX(unit_price) p1, COUNT(*) nv FROM service_catalog GROUP BY service_code, service_category)
SELECT service_category, COUNT(*) services, ROUND(MIN((p1-p0)/p0*100),1) min_pct, ROUND(AVG((p1-p0)/p0*100),1) avg_pct, ROUND(MAX((p1-p0)/p0*100),1) max_pct, MIN(nv) min_versions, MAX(nv) max_versions
FROM p GROUP BY service_category;

SELECT '## Q05 진료 1건당 서비스 라인 수 분포' AS section;
SELECT n lines_per_encounter, COUNT(*) encounters FROM (SELECT encounter_id, COUNT(*) n FROM encounter_services GROUP BY encounter_id) t GROUP BY n ORDER BY n;

SELECT '## Q06 수량 분포' AS section;
SELECT quantity, COUNT(*) n FROM encounter_services GROUP BY quantity ORDER BY quantity;

SELECT '## Q07 분류별 매출 (라인 금액 합)' AS section;
SELECT c.service_category, COUNT(*) n_lines, SUM(es.line_amount) revenue, ROUND(SUM(es.line_amount)/(SELECT SUM(line_amount) FROM encounter_services)*100,2) share_pct, ROUND(AVG(es.quantity),3) avg_qty
FROM encounter_services es JOIN service_catalog c ON c.service_version_id = es.service_version_id GROUP BY c.service_category ORDER BY revenue DESC;

SELECT '## Q08 서비스 코드별 매출 상위 20과 누적 비중' AS section;
WITH r AS (SELECT c.service_code, MAX(c.service_name) service_name, MAX(c.service_category) cat, COUNT(*) n_lines, SUM(es.line_amount) revenue
           FROM encounter_services es JOIN service_catalog c ON c.service_version_id = es.service_version_id GROUP BY c.service_code),
     k AS (SELECT r.*, ROW_NUMBER() OVER (ORDER BY revenue DESC) rk, SUM(revenue) OVER (ORDER BY revenue DESC) cum, SUM(revenue) OVER () tot FROM r)
SELECT rk, service_code, service_name, cat, n_lines, revenue, ROUND(revenue/tot*100,2) share_pct, ROUND(cum/tot*100,1) cum_pct FROM k WHERE rk <= 20 OR rk IN (30,40,50,60) ORDER BY rk;

SELECT '## Q09 서비스 코드별 이용 건수 분포 (최소/사분위/최대)' AS section;
WITH r AS (SELECT c.service_code, COUNT(*) n_lines FROM encounter_services es JOIN service_catalog c ON c.service_version_id = es.service_version_id GROUP BY c.service_code),
     k AS (SELECT n_lines, NTILE(4) OVER (ORDER BY n_lines) q FROM r)
SELECT q, COUNT(*) services, MIN(n_lines) min_lines, MAX(n_lines) max_lines FROM k GROUP BY q ORDER BY q;

SELECT '## Q10 레거시 시스템별 진료 청구 구조' AS section;
WITH s AS (SELECT encounter_id, COUNT(*) nl, SUM(quantity) q, SUM(line_amount) amt FROM encounter_services GROUP BY encounter_id)
SELECT e.source_system, COUNT(*) encounters, ROUND(AVG(e.gross_charge)) avg_gross, ROUND(AVG(s.nl),3) avg_lines, ROUND(AVG(s.q),3) avg_qty, ROUND(AVG(s.amt)) avg_line_sum
FROM encounters e LEFT JOIN s ON s.encounter_id = e.encounter_id GROUP BY e.source_system;

SELECT '## Q11 청구액 구간 분포' AS section;
SELECT FLOOR(gross_charge/10000)*10000 bucket, COUNT(*) n FROM encounters GROUP BY bucket ORDER BY bucket;

SELECT '## Q12 연도별 평균 단가·청구' AS section;
SELECT YEAR(e.started_at) y, COUNT(DISTINCT e.encounter_id) encounters, ROUND(AVG(es.unit_price)) avg_unit, ROUND(SUM(es.line_amount)/COUNT(DISTINCT e.encounter_id)) amt_per_enc
FROM encounters e JOIN encounter_services es ON es.encounter_id = e.encounter_id GROUP BY y ORDER BY y;

SELECT '## Q13 진료과별 진료 건수·평균 청구' AS section;
WITH d AS (SELECT e.encounter_id, e.gross_charge, h.department_code, h.hospital_id FROM encounters e
           JOIN checkins c ON c.checkin_id = e.checkin_id JOIN clinic_sessions s ON s.session_id = c.session_id
           JOIN hospital_departments h ON h.hospital_department_id = s.hospital_department_id)
SELECT d.department_code, MAX(dp.department_name) dept, COUNT(*) encounters, ROUND(AVG(gross_charge)) avg_gross, MIN(gross_charge) min_g, MAX(gross_charge) max_g
FROM d JOIN departments dp ON dp.department_code = d.department_code GROUP BY d.department_code ORDER BY d.department_code;

SELECT '## Q14 진료과 x 서비스 분류 매출 비중' AS section;
WITH d AS (SELECT e.encounter_id, h.department_code FROM encounters e
           JOIN checkins c ON c.checkin_id = e.checkin_id JOIN clinic_sessions s ON s.session_id = c.session_id
           JOIN hospital_departments h ON h.hospital_department_id = s.hospital_department_id),
     x AS (SELECT d.department_code, sc.service_category, SUM(es.line_amount) amt, COUNT(*) n_lines
           FROM d JOIN encounter_services es ON es.encounter_id = d.encounter_id JOIN service_catalog sc ON sc.service_version_id = es.service_version_id
           GROUP BY d.department_code, sc.service_category)
SELECT department_code, service_category, n_lines, amt, ROUND(amt / SUM(amt) OVER (PARTITION BY department_code) * 100, 1) share_pct FROM x ORDER BY department_code, service_category;

SELECT '## Q15 진료과별 사용 서비스 종류 수와 상위 서비스 집중도' AS section;
WITH d AS (SELECT e.encounter_id, h.department_code FROM encounters e
           JOIN checkins c ON c.checkin_id = e.checkin_id JOIN clinic_sessions s ON s.session_id = c.session_id
           JOIN hospital_departments h ON h.hospital_department_id = s.hospital_department_id),
     x AS (SELECT d.department_code, sc.service_code, SUM(es.line_amount) amt FROM d JOIN encounter_services es ON es.encounter_id = d.encounter_id
           JOIN service_catalog sc ON sc.service_version_id = es.service_version_id GROUP BY d.department_code, sc.service_code),
     k AS (SELECT x.*, ROW_NUMBER() OVER (PARTITION BY department_code ORDER BY amt DESC) rk, SUM(amt) OVER (PARTITION BY department_code) tot FROM x)
SELECT department_code, COUNT(*) services_used, ROUND(SUM(CASE WHEN rk <= 5 THEN amt END)/MAX(tot)*100,1) top5_share_pct, MAX(CASE WHEN rk = 1 THEN service_code END) top1 FROM k GROUP BY department_code ORDER BY department_code;

SELECT '## Q16 병원별 진료과 수 분포' AS section;
SELECT n_dept, COUNT(*) hospitals FROM (SELECT hospital_id, COUNT(*) n_dept FROM hospital_departments GROUP BY hospital_id) t GROUP BY n_dept ORDER BY n_dept;

SELECT '## Q17 병원별 진료 건수·매출 분위 (상위 집중도)' AS section;
WITH d AS (SELECT h.hospital_id, COUNT(*) enc, SUM(e.gross_charge) rev FROM encounters e
           JOIN checkins c ON c.checkin_id = e.checkin_id JOIN clinic_sessions s ON s.session_id = c.session_id
           JOIN hospital_departments h ON h.hospital_department_id = s.hospital_department_id GROUP BY h.hospital_id),
     k AS (SELECT d.*, NTILE(10) OVER (ORDER BY rev DESC) dec10 FROM d)
SELECT dec10, COUNT(*) hospitals, MIN(enc) min_enc, MAX(enc) max_enc, SUM(rev) rev, ROUND(SUM(rev)/(SELECT SUM(rev) FROM d)*100,1) share_pct FROM k GROUP BY dec10 ORDER BY dec10;

SELECT '## Q18 병원 유형·진료과 수별 병원당 진료' AS section;
WITH d AS (SELECT h.hospital_id, COUNT(*) enc FROM encounters e
           JOIN checkins c ON c.checkin_id = e.checkin_id JOIN clinic_sessions s ON s.session_id = c.session_id
           JOIN hospital_departments h ON h.hospital_department_id = s.hospital_department_id GROUP BY h.hospital_id),
     nd AS (SELECT hospital_id, COUNT(*) n_dept FROM hospital_departments GROUP BY hospital_id)
SELECT hp.hospital_type, nd.n_dept, COUNT(*) hospitals, ROUND(AVG(d.enc)) avg_enc FROM hospitals hp JOIN nd ON nd.hospital_id = hp.hospital_id
LEFT JOIN d ON d.hospital_id = hp.hospital_id GROUP BY hp.hospital_type, nd.n_dept ORDER BY hp.hospital_type, nd.n_dept;

SELECT '## Q19 연도별 배치 의사 vs 세션 담당 의사' AS section;
SELECT y, assigned, active, ROUND(active/assigned*100,1) pct FROM (
  SELECT YEAR(a.valid_from) y, COUNT(DISTINCT a.doctor_id) assigned,
         COUNT(DISTINCT CASE WHEN s.assignment_id IS NOT NULL THEN a.doctor_id END) active
  FROM doctor_assignments a LEFT JOIN (SELECT DISTINCT assignment_id FROM clinic_sessions) s ON s.assignment_id = a.assignment_id
  GROUP BY YEAR(a.valid_from)) t ORDER BY y;

SELECT '## Q20 레거시 시스템 비율 (테이블별)' AS section;
SELECT 'hospitals' t, source_system, COUNT(*) n FROM hospitals GROUP BY source_system
UNION ALL SELECT 'patients', source_system, COUNT(*) FROM patients GROUP BY source_system
UNION ALL SELECT 'encounters', source_system, COUNT(*) FROM encounters GROUP BY source_system
UNION ALL SELECT 'payments', source_system, COUNT(*) FROM payments GROUP BY source_system;

SELECT '## Q21 병원의 레거시 시스템과 진료의 레거시 시스템 일치' AS section;
SELECT hp.source_system hosp_sys, e.source_system enc_sys, COUNT(*) n FROM encounters e
JOIN checkins c ON c.checkin_id = e.checkin_id JOIN clinic_sessions s ON s.session_id = c.session_id
JOIN hospital_departments h ON h.hospital_department_id = s.hospital_department_id JOIN hospitals hp ON hp.hospital_id = h.hospital_id
GROUP BY hp.source_system, e.source_system;

USE team3_medallion_dq;
SELECT '## Q22 격리·제외 테이블별 건수와 직접/연쇄' AS section;
SELECT 'doctors' t, quarantine_type, COUNT(*) n FROM doctors_quarantine GROUP BY quarantine_type
UNION ALL SELECT 'doctor_assignments', quarantine_type, COUNT(*) FROM doctor_assignments_quarantine GROUP BY quarantine_type
UNION ALL SELECT 'clinic_sessions', quarantine_type, COUNT(*) FROM clinic_sessions_quarantine GROUP BY quarantine_type
UNION ALL SELECT 'appointment_slots', quarantine_type, COUNT(*) FROM appointment_slots_quarantine GROUP BY quarantine_type
UNION ALL SELECT 'checkins', quarantine_type, COUNT(*) FROM checkins_quarantine GROUP BY quarantine_type
UNION ALL SELECT 'payments_quarantine', NULL, COUNT(*) FROM payments_quarantine
UNION ALL SELECT 'payments_excluded', NULL, COUNT(*) FROM payments_excluded
UNION ALL SELECT 'hospital_departments_q', NULL, COUNT(*) FROM hospital_departments_quarantine
UNION ALL SELECT 'dq.encounters', NULL, COUNT(*) FROM encounters
UNION ALL SELECT 'dq.encounter_services', NULL, COUNT(*) FROM encounter_services;

SELECT '## Q23 재정제(reclean) 격리: 테이블 x 주요 사유' AS section;
SELECT table_name, primary_reason, quarantine_kind, COUNT(*) n FROM reclean_quarantine GROUP BY table_name, primary_reason, quarantine_kind ORDER BY table_name, n DESC;

SELECT '## Q24 재정제 이슈: 테이블 x 규칙' AS section;
SELECT table_name, rule_code, issue_kind, COUNT(*) n FROM reclean_issues GROUP BY table_name, rule_code, issue_kind ORDER BY table_name, n DESC;

SELECT '## Q25 재정제 복구: 테이블 x 근거' AS section;
SELECT table_name, basis, COUNT(*) n FROM reclean_repairs GROUP BY table_name, basis ORDER BY table_name, n DESC;

SELECT '## Q26 레거시 시스템별 격리 비율 (내 담당 5개 테이블)' AS section;
SELECT 'checkins' t, q.source_system, q.n quarantined, c.n clean, ROUND(q.n/(q.n+c.n)*100,2) q_pct
FROM (SELECT TRIM(source_system) source_system, COUNT(*) n FROM checkins_quarantine GROUP BY TRIM(source_system)) q
JOIN (SELECT source_system, COUNT(*) n FROM team3_medallion.checkins GROUP BY source_system) c ON c.source_system = q.source_system
UNION ALL
SELECT 'clinic_sessions', q.source_system, q.n, c.n, ROUND(q.n/(q.n+c.n)*100,2)
FROM (SELECT TRIM(source_system) source_system, COUNT(*) n FROM clinic_sessions_quarantine GROUP BY TRIM(source_system)) q
JOIN (SELECT source_system, COUNT(*) n FROM team3_medallion.clinic_sessions GROUP BY source_system) c ON c.source_system = q.source_system;

SELECT '## Q27 reclean_finance_before: 불일치 진료' AS section;
SELECT mismatch, COUNT(*) n, SUM(gross_charge) gross, SUM(ABS(gross_charge - service_total)) svc_gap, SUM(ABS(net_charge - (payment_total - refund_total))) pay_gap FROM reclean_finance_before GROUP BY mismatch;
