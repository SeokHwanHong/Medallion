-- 08. 발표용 DB 기준 사실 확인 (조회 전용: SELECT 만 사용)
SET SESSION TRANSACTION READ ONLY;
SET SESSION sql_big_selects = 1;
USE team3_medallion_dq;

SELECT '## F01 재정제 격리: 테이블 x 원천 x 직접/연쇄' AS section;
SELECT table_name, TRIM(JSON_UNQUOTE(JSON_EXTRACT(original_row, '$.source_system'))) src, quarantine_kind, COUNT(*) n
FROM reclean_quarantine GROUP BY table_name, src, quarantine_kind ORDER BY table_name, src, quarantine_kind;

SELECT '## F02 재정제 제외(중복): 테이블 x 원천' AS section;
SELECT table_name, TRIM(JSON_UNQUOTE(JSON_EXTRACT(original_row, '$.source_system'))) src, COUNT(*) n
FROM reclean_excluded_mirrors GROUP BY table_name, src ORDER BY table_name, src;

USE team3_medallion;
SELECT '## F03 기준정보 테이블 원천' AS section;
SELECT 'service_catalog' t, source_system src, COUNT(*) n FROM service_catalog GROUP BY source_system
UNION ALL SELECT 'departments', source_system, COUNT(*) FROM departments GROUP BY source_system
UNION ALL SELECT 'code_dictionary', source_system, COUNT(*) FROM code_dictionary GROUP BY source_system
UNION ALL SELECT 'legacy_code_mappings', source_system, COUNT(*) FROM legacy_code_mappings GROUP BY source_system;

SELECT '## F04 원천 코드 매핑: A와 B가 같은 매핑' AS section;
SELECT COUNT(*) a_rows, SUM(b.mapping_id IS NOT NULL) same_in_b
FROM legacy_code_mappings a
LEFT JOIN legacy_code_mappings b ON b.source_system = 'LEGACY_B' AND b.domain = a.domain AND b.raw_code = a.raw_code AND b.standard_code = a.standard_code
WHERE a.source_system = 'LEGACY_A';

SELECT '## F05 예약 이벤트 시각 (예약 시각 기준, 분)' AS section;
SELECT source_system src, event_type, COUNT(*) n,
       MIN(TIMESTAMPDIFF(MINUTE, scheduled_at, event_at)) min_min, MAX(TIMESTAMPDIFF(MINUTE, scheduled_at, event_at)) max_min,
       ROUND(AVG(event_at < scheduled_at) * 100, 1) before_pct
FROM appointment_events WHERE event_type IN ('CANCELLED', 'NO_SHOW', 'COMPLETED')
GROUP BY source_system, event_type ORDER BY src, event_type;

SELECT '## F06 예약 최종 상태 (원천별)' AS section;
SELECT source_system src, status, COUNT(*) n, ROUND(COUNT(*) / SUM(COUNT(*)) OVER (PARTITION BY source_system) * 100, 2) pct
FROM appointments GROUP BY source_system, status ORDER BY src, status;
