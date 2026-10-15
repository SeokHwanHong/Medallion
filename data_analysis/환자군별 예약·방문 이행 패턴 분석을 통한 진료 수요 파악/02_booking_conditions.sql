-- MySQL Workbench: execute the complete query, then export Result Grid as CSV with column names.
-- 주장 2: 같은 환자군·진료과 내 채널·선행기간 비교
-- MySQL 8 / 조회 전용。DB 실행 검증은 하지 않음.
-- 독립 실행: WITH부터 마지막 SELECT의 세미콜론까지 전체 선택.
-- analysis_params에서 기간 지정. 기본값 2023년 1월, 종료일 미포함.
-- 테이블/데이터/세션 변경 없음. 조회도 부하가 있으므로 범위 검토 후 사용.
-- 전제: 정제 DB의 부모 PK가 유일함. UNKNOWN은 제외하지 않고 별도 표시.
WITH analysis_params AS (
    SELECT CAST('2023-01-01' AS DATETIME) AS period_start,
           CAST('2023-02-01' AS DATETIME) AS period_end_exclusive,
           CAST('2026-01-01' AS DATETIME) AS observation_end_exclusive
),
booking_seed AS (
    SELECT a.appointment_id, a.patient_id, a.status, a.channel,
           a.booked_at, a.scheduled_at,
           DATE_FORMAT(a.scheduled_at, '%Y-%m') AS visit_month,
           sl.session_id AS expected_session_id,
           hd.hospital_id, hd.department_code,
           CASE WHEN p.sex_code IN ('F','M','U') THEN p.sex_code ELSE 'UNKNOWN' END AS sex_group,
           CASE WHEN p.patient_id IS NULL OR p.birth_date IS NULL
                     OR YEAR(p.birth_date)=0 OR MONTH(p.birth_date)=0 OR DAYOFMONTH(p.birth_date)=0
                     OR p.birth_date>DATE(a.scheduled_at) THEN NULL
                WHEN TIMESTAMPDIFF(YEAR,p.birth_date,DATE(a.scheduled_at)) BETWEEN 0 AND 120
                THEN TIMESTAMPDIFF(YEAR,p.birth_date,DATE(a.scheduled_at)) ELSE NULL END AS age_at_visit,
           (p.patient_id IS NULL) AS missing_patient,
           (p.patient_id IS NOT NULL AND sl.slot_id IS NOT NULL AND cs.session_id IS NOT NULL
            AND hd.hospital_department_id IS NOT NULL AND h.hospital_id IS NOT NULL
            AND d.department_code IS NOT NULL) AS parent_complete
    FROM team3_medallion.appointments a
    LEFT JOIN team3_medallion.patients p ON p.patient_id=a.patient_id
    LEFT JOIN team3_medallion.appointment_slots sl ON sl.slot_id=a.slot_id
    LEFT JOIN team3_medallion.clinic_sessions cs ON cs.session_id=sl.session_id
    LEFT JOIN team3_medallion.hospital_departments hd ON hd.hospital_department_id=cs.hospital_department_id
    LEFT JOIN team3_medallion.hospitals h ON h.hospital_id=hd.hospital_id
    LEFT JOIN team3_medallion.departments d ON d.department_code=hd.department_code
    CROSS JOIN analysis_params ap
    WHERE a.scheduled_at>=ap.period_start
      AND a.scheduled_at<LEAST(ap.period_end_exclusive,ap.observation_end_exclusive)
),
booking_base AS (
    SELECT s.*,
           CASE WHEN age_at_visit IS NULL THEN 'UNKNOWN'
                WHEN age_at_visit<20 THEN '0-19' WHEN age_at_visit<40 THEN '20-39'
                WHEN age_at_visit<60 THEN '40-59' WHEN age_at_visit<80 THEN '60-79'
                ELSE '80+' END AS age_group,
           CASE WHEN booked_at IS NULL OR booked_at>scheduled_at THEN 'UNKNOWN'
                WHEN TIMESTAMPDIFF(DAY,booked_at,scheduled_at)<7 THEN '0-6'
                WHEN TIMESTAMPDIFF(DAY,booked_at,scheduled_at)<14 THEN '7-13'
                WHEN TIMESTAMPDIFF(DAY,booked_at,scheduled_at)<21 THEN '14-20'
                ELSE '21+' END AS lead_group
    FROM booking_seed s
)
, metrics AS (
    SELECT visit_month,age_group,sex_group,department_code,channel,lead_group,
           COUNT(*) AS booking_count,
           COUNT(DISTINCT patient_id) AS unique_patients,
           SUM(status='CANCELLED') AS cancelled_count,
           SUM(status='NO_SHOW') AS no_show_count
    FROM booking_base WHERE parent_complete=1
    GROUP BY visit_month,age_group,sex_group,department_code,channel,lead_group
)
SELECT m.*,
       ROUND(100.0*cancelled_count/NULLIF(booking_count,0),2) AS cancelled_pct,
       ROUND(100.0*no_show_count/NULLIF(booking_count,0),2) AS no_show_pct,
       ROUND(100.0*no_show_count/NULLIF(booking_count,0)
             -100.0*SUM(no_show_count) OVER(PARTITION BY visit_month,age_group,sex_group,department_code)
              /NULLIF(SUM(booking_count) OVER(PARTITION BY visit_month,age_group,sex_group,department_code),0),2)
           AS no_show_diff_vs_peer_pp,
       (booking_count<30) AS small_sample
FROM metrics m
ORDER BY visit_month,department_code,age_group,sex_group,channel,lead_group;
