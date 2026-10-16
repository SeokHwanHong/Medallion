-- 07. 공통 기준정보(A) - A/B 기록 연결 점검, Silver 기준 (조회 전용: SELECT 만 사용)
SET SESSION TRANSACTION READ ONLY;
SET SESSION sql_big_selects = 1;
USE team3_medallion;

SELECT '## M01 단가표: 행 수, 음수 단가, 하이픈 ID, 원천' AS section;
SELECT COUNT(*) n_rows, SUM(unit_price < 0) neg_price, SUM(service_version_id LIKE '%-%') hyphen_id,
       SUM(source_system = 'LEGACY_A') src_a, SUM(source_system = 'LEGACY_B') src_b FROM service_catalog;

SELECT '## M02 원본에서 오류였던 단가표 7행의 Silver 상태' AS section;
SELECT service_version_id, service_code, valid_from, valid_to, unit_price, source_system FROM service_catalog
WHERE REPLACE(service_version_id, '-', '_') IN ('SVV_000000010','SVV_000000057','SVV_000000104','SVV_000000151','SVV_000000041','SVV_000000088','SVV_000000135')
ORDER BY service_version_id;

SELECT '## M03 위 7개 버전을 쓰는 Silver 진료 서비스 줄 (원천별)' AS section;
SELECT es.service_version_id, es.source_system, COUNT(*) n_lines, MIN(es.unit_price) min_line_price, MAX(es.unit_price) max_line_price
FROM encounter_services es
WHERE es.service_version_id IN ('SVV_000000010','SVV_000000057','SVV_000000104','SVV_000000151','SVV_000000041','SVV_000000088','SVV_000000135')
GROUP BY es.service_version_id, es.source_system ORDER BY es.service_version_id, es.source_system;

SELECT '## M04 Silver 진료 서비스 -> 단가표 연결 점검 (원천별)' AS section;
SELECT es.source_system, COUNT(*) n_lines,
       SUM(sc.service_version_id IS NULL) not_in_catalog,
       SUM(sc.service_version_id IS NOT NULL AND es.unit_price <> sc.unit_price) price_ne_catalog,
       SUM(sc.service_version_id IS NOT NULL AND DATE(e.started_at) NOT BETWEEN sc.valid_from AND sc.valid_to) version_out_of_period
FROM encounter_services es
LEFT JOIN service_catalog sc ON sc.service_version_id = es.service_version_id
LEFT JOIN encounters e ON e.encounter_id = es.encounter_id
GROUP BY es.source_system;

SELECT '## M05 Silver 진료과 연결 (원천별)' AS section;
SELECT 'hospital_departments' t, h.source_system, COUNT(*) n_rows, SUM(d.department_code IS NULL) not_in_departments
FROM hospital_departments h LEFT JOIN departments d ON d.department_code = h.department_code GROUP BY h.source_system
UNION ALL
SELECT 'doctors', dc.source_system, COUNT(*), SUM(d.department_code IS NULL)
FROM doctors dc LEFT JOIN departments d ON d.department_code = dc.department_code GROUP BY dc.source_system;

USE team3_medallion_dq;
SELECT '## M06 격리된 진료 서비스 중 7개 버전을 가리키는 행 (재정제 기록, 원천 x 사유)' AS section;
SELECT JSON_UNQUOTE(JSON_EXTRACT(original_row, '$.source_system')) src, primary_reason, quarantine_kind, COUNT(*) n
FROM reclean_quarantine
WHERE table_name = 'encounter_services'
  AND REPLACE(TRIM(JSON_UNQUOTE(JSON_EXTRACT(original_row, '$.service_version_id'))), '-', '_')
      IN ('SVV_000000010','SVV_000000057','SVV_000000104','SVV_000000151','SVV_000000041','SVV_000000088','SVV_000000135')
GROUP BY src, primary_reason, quarantine_kind ORDER BY src, n DESC;

SELECT '## M07 단가표 관련 재정제 복구·격리 기록' AS section;
SELECT 'repairs' kind, table_name, COUNT(*) n FROM reclean_repairs WHERE table_name = 'service_catalog' GROUP BY table_name
UNION ALL
SELECT 'quarantine', table_name, COUNT(*) FROM reclean_quarantine WHERE table_name = 'service_catalog' GROUP BY table_name
UNION ALL
SELECT 'cross_recovery', table_name, COUNT(*) FROM cross_recovery_log_20261015 WHERE table_name = 'service_catalog' GROUP BY table_name;
