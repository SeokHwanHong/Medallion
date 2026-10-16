-- 03: 월×진료과×요일(월=0)×도착 1시간 구간. 존재하지 않는 구간은 생성하지 않음.
-- MySQL 8 / 조회 전용. DB 접속·실행·실행 계획 검증 없음.
-- 전체 기간 2023-01-01 이상 ~ 2026-01-01 미만, 월별 집계. 각 파일 독립 실행.
-- 현재 team3_medallion 정제 스냅샷. 원본 또는 다른 정제 작업본을 자동 반영하지 않음.
-- 분석 단위는 접수 기록. 고유 환자 수/확정 방문 수 아님. 부모 PK 유일성 전제.
-- 월별 *_rows 진단/비교분모는 여러 결과 행에 반복됨. 합산 금지.
-- key_or_join_issue=1이면 집계를 해석하기 전에 원본 키/부모 조인 확인.
WITH analysis_params AS (
    SELECT CAST('2023-01-01' AS DATETIME) AS period_start,
           CAST('2026-01-01' AS DATETIME) AS period_end_exclusive
), walk_in_source AS (
    SELECT c.checkin_id,c.patient_id,c.session_id,c.arrival_at,c.outcome,
           DATE_FORMAT(c.arrival_at,'%Y-%m') AS arrival_month,
           WEEKDAY(c.arrival_at) AS weekday_monday_zero,
           HOUR(c.arrival_at) AS arrival_hour
    FROM team3_medallion.checkins c CROSS JOIN analysis_params ap
    WHERE c.visit_type='WALK_IN'
      AND c.arrival_at>=ap.period_start AND c.arrival_at<ap.period_end_exclusive
), source_month AS (
    SELECT arrival_month,COUNT(*) AS source_walk_in_rows,
           COUNT(DISTINCT checkin_id) AS source_unique_checkin_ids,
           SUM(CASE WHEN checkin_id IS NULL OR TRIM(checkin_id)='' THEN 1 ELSE 0 END) AS source_missing_checkin_id_rows
    FROM walk_in_source GROUP BY arrival_month
), joined_base AS (
    SELECT c.*,
           CASE WHEN c.outcome IN ('SEEN','LEFT','REJECTED') THEN c.outcome ELSE 'UNKNOWN' END AS outcome_group,
           CASE WHEN d.department_code IS NULL OR TRIM(d.department_code)='' THEN 'UNKNOWN'
                ELSE d.department_code END AS department_code,
           CASE WHEN d.department_code IS NULL OR TRIM(d.department_code)='' THEN 'UNKNOWN'
                ELSE COALESCE(d.department_name,'UNKNOWN') END AS department_name,
           CASE WHEN d.department_code IS NULL OR TRIM(d.department_code)='' THEN 1 ELSE 0 END AS department_unknown,
           CASE WHEN cs.session_id IS NULL THEN 1 ELSE 0 END AS missing_session,
           CASE WHEN hd.hospital_department_id IS NULL THEN 1 ELSE 0 END AS missing_hospital_department,
           CASE WHEN h.hospital_id IS NULL THEN 1 ELSE 0 END AS missing_hospital,
           CASE WHEN d.department_code IS NULL OR TRIM(d.department_code)='' THEN 1 ELSE 0 END AS missing_department,
           CASE WHEN p.patient_id IS NULL THEN 1 ELSE 0 END AS missing_patient,
           p.birth_date,
           CASE WHEN p.sex_code IN ('F','M','U') THEN p.sex_code ELSE 'UNKNOWN' END AS sex_group
    FROM walk_in_source c
    LEFT JOIN team3_medallion.clinic_sessions cs ON cs.session_id=c.session_id
    LEFT JOIN team3_medallion.hospital_departments hd ON hd.hospital_department_id=cs.hospital_department_id
    LEFT JOIN team3_medallion.departments d ON d.department_code=hd.department_code
    LEFT JOIN team3_medallion.hospitals h ON h.hospital_id=hd.hospital_id
    LEFT JOIN team3_medallion.patients p ON p.patient_id=c.patient_id
    -- hospitals/patients 조인은 부모 연결 진단용. 연결 누락을 이유로 접수를 제외하지 않음.
), month_diagnostics AS (
    SELECT s.arrival_month,s.source_walk_in_rows,s.source_unique_checkin_ids,s.source_missing_checkin_id_rows,
           COUNT(*) AS joined_walk_in_rows,
           COUNT(DISTINCT b.checkin_id) AS joined_unique_checkin_ids,
           COUNT(*)-s.source_walk_in_rows AS join_extra_rows,
           s.source_walk_in_rows-s.source_unique_checkin_ids AS source_duplicate_or_null_id_rows,
           CASE WHEN s.source_walk_in_rows<>s.source_unique_checkin_ids OR s.source_missing_checkin_id_rows>0
                THEN 1 ELSE 0 END AS source_key_issue,
           CASE WHEN COUNT(*)<>s.source_walk_in_rows THEN 1 ELSE 0 END AS join_amplification_issue,
           CASE WHEN COUNT(*)<>s.source_walk_in_rows OR s.source_walk_in_rows<>s.source_unique_checkin_ids
                     OR s.source_missing_checkin_id_rows>0 THEN 1 ELSE 0 END AS key_or_join_issue
    FROM source_month s JOIN joined_base b ON b.arrival_month=s.arrival_month
    GROUP BY s.arrival_month,s.source_walk_in_rows,s.source_unique_checkin_ids,s.source_missing_checkin_id_rows
)
, metrics AS (
    SELECT arrival_month,department_code,department_name,department_unknown,weekday_monday_zero,arrival_hour,
           COUNT(*) AS walk_in_count,
           COUNT(DISTINCT checkin_id) AS unique_checkin_count,
           SUM(CASE WHEN outcome_group='SEEN' THEN 1 ELSE 0 END) AS seen_count,
           SUM(CASE WHEN outcome_group='LEFT' THEN 1 ELSE 0 END) AS left_count,
           SUM(CASE WHEN outcome_group='REJECTED' THEN 1 ELSE 0 END) AS rejected_count,
           SUM(CASE WHEN outcome_group='UNKNOWN' THEN 1 ELSE 0 END) AS unknown_outcome_count,
           SUM(CASE WHEN missing_session=1 THEN 1 ELSE 0 END) AS missing_session_count,
           SUM(CASE WHEN missing_hospital_department=1 THEN 1 ELSE 0 END) AS missing_hospital_department_count,
           SUM(CASE WHEN missing_hospital=1 THEN 1 ELSE 0 END) AS missing_hospital_count,
           SUM(CASE WHEN missing_department=1 THEN 1 ELSE 0 END) AS missing_department_count,
           SUM(CASE WHEN missing_patient=1 THEN 1 ELSE 0 END) AS missing_patient_count
    FROM joined_base
    GROUP BY arrival_month,department_code,department_name,department_unknown,weekday_monday_zero,arrival_hour
), department_totals AS (
    SELECT m.*,
           SUM(walk_in_count) OVER(PARTITION BY arrival_month,department_code) AS department_month_walk_in_count,
           SUM(rejected_count) OVER(PARTITION BY arrival_month,department_code) AS department_month_rejected_count
    FROM metrics m
)
-- 비교 기준은 같은 월·진료과의 모든 관측 요일·시간대(대상 구간 자신 포함).
SELECT m.*,
       ROUND(100.0*m.seen_count/NULLIF(m.walk_in_count,0),2) AS seen_pct,
       ROUND(100.0*m.left_count/NULLIF(m.walk_in_count,0),2) AS left_pct,
       ROUND(100.0*m.rejected_count/NULLIF(m.walk_in_count,0),2) AS rejected_pct,
       ROUND(100.0*m.unknown_outcome_count/NULLIF(m.walk_in_count,0),2) AS unknown_outcome_pct,
       CASE WHEN m.walk_in_count<30 THEN 1 ELSE 0 END AS small_sample,
       ROUND(100.0*m.department_month_rejected_count/NULLIF(m.department_month_walk_in_count,0),2) AS department_month_rejected_pct,
       ROUND(100.0*m.rejected_count/NULLIF(m.walk_in_count,0)
             -100.0*m.department_month_rejected_count/NULLIF(m.department_month_walk_in_count,0),2) AS rejected_diff_vs_department_month_pp,
       ROUND(100.0*m.rejected_count/NULLIF(m.department_month_rejected_count,0),2) AS rejected_share_of_department_month_pct,
       d.source_walk_in_rows,d.source_unique_checkin_ids,d.source_missing_checkin_id_rows,
       d.joined_walk_in_rows,d.joined_unique_checkin_ids,d.join_extra_rows,
       d.source_duplicate_or_null_id_rows,d.source_key_issue,d.join_amplification_issue,d.key_or_join_issue
FROM department_totals m JOIN month_diagnostics d ON d.arrival_month=m.arrival_month
ORDER BY m.arrival_month,department_code,weekday_monday_zero,arrival_hour;
