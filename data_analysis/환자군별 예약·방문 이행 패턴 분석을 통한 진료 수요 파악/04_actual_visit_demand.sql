-- MySQL Workbench: execute the complete query, then export Result Grid as CSV with column names.
-- 주장 4: 진료과·요일·시간대별 관측 수요와 환자군 구성
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
arrival_seed AS (
    SELECT c.checkin_id,c.patient_id,c.session_id,c.arrival_at,c.visit_type,c.outcome,
           hd.hospital_id,hd.department_code,
           CASE WHEN p.sex_code IN ('F','M','U') THEN p.sex_code ELSE 'UNKNOWN' END AS sex_group,
           CASE WHEN p.patient_id IS NULL OR p.birth_date IS NULL
                     OR YEAR(p.birth_date)=0 OR MONTH(p.birth_date)=0 OR DAYOFMONTH(p.birth_date)=0
                     OR p.birth_date>DATE(c.arrival_at) THEN NULL
                WHEN TIMESTAMPDIFF(YEAR,p.birth_date,DATE(c.arrival_at)) BETWEEN 0 AND 120
                THEN TIMESTAMPDIFF(YEAR,p.birth_date,DATE(c.arrival_at)) ELSE NULL END AS age_at_arrival,
           (p.patient_id IS NOT NULL AND cs.session_id IS NOT NULL
            AND hd.hospital_department_id IS NOT NULL AND h.hospital_id IS NOT NULL
            AND d.department_code IS NOT NULL) AS parent_complete
    FROM team3_medallion.checkins c
    LEFT JOIN team3_medallion.patients p ON p.patient_id=c.patient_id
    LEFT JOIN team3_medallion.clinic_sessions cs ON cs.session_id=c.session_id
    LEFT JOIN team3_medallion.hospital_departments hd ON hd.hospital_department_id=cs.hospital_department_id
    LEFT JOIN team3_medallion.hospitals h ON h.hospital_id=hd.hospital_id
    LEFT JOIN team3_medallion.departments d ON d.department_code=hd.department_code
    CROSS JOIN analysis_params ap
    WHERE c.arrival_at>=ap.period_start
      AND c.arrival_at<LEAST(ap.period_end_exclusive,ap.observation_end_exclusive)
), arrival_groups AS (
    SELECT hospital_id,department_code,patient_id,session_id,arrival_at,sex_group,parent_complete,
           CASE WHEN age_at_arrival IS NULL THEN 'UNKNOWN'
                WHEN age_at_arrival<20 THEN '0-19' WHEN age_at_arrival<40 THEN '20-39'
                WHEN age_at_arrival<60 THEN '40-59' WHEN age_at_arrival<80 THEN '60-79'
                ELSE '80+' END AS age_group,
           COUNT(*) AS checkin_records,
           SUM(CASE WHEN visit_type='RESERVED' THEN 1 ELSE 0 END) AS reserved_records,
           SUM(CASE WHEN visit_type='WALK_IN' THEN 1 ELSE 0 END) AS walk_in_records,
           SUM(CASE WHEN outcome='SEEN' THEN 1 ELSE 0 END) AS seen_records,
           SUM(CASE WHEN outcome='LEFT' THEN 1 ELSE 0 END) AS left_records,
           SUM(CASE WHEN outcome='REJECTED' THEN 1 ELSE 0 END) AS rejected_records
    FROM arrival_seed
    GROUP BY hospital_id,department_code,patient_id,session_id,arrival_at,sex_group,parent_complete,age_at_arrival
), metrics AS (
    SELECT hospital_id,department_code,DATE_FORMAT(arrival_at,'%Y-%m') AS arrival_month,
           WEEKDAY(arrival_at) AS weekday_monday_zero,HOUR(arrival_at) AS arrival_hour,
           age_group,sex_group,parent_complete,
           SUM(checkin_records) AS observed_checkin_records,
           COUNT(*) AS patient_session_arrival_groups,
           COUNT(DISTINCT patient_id) AS unique_patient_ids,
           COUNT(DISTINCT DATE(arrival_at)) AS dates_with_observed_arrivals,
           SUM(checkin_records>1) AS repeated_arrival_groups,
           SUM(reserved_records) AS reserved_records,SUM(walk_in_records) AS walk_in_records,
           SUM(seen_records) AS seen_records,SUM(left_records) AS left_records,SUM(rejected_records) AS rejected_records
    FROM arrival_groups
    GROUP BY hospital_id,department_code,DATE_FORMAT(arrival_at,'%Y-%m'),
             WEEKDAY(arrival_at),HOUR(arrival_at),age_group,sex_group,parent_complete
)
SELECT m.*,
       ROUND(100.0*walk_in_records/NULLIF(observed_checkin_records,0),2) AS walk_in_record_pct,
       ROUND(100.0*observed_checkin_records
         /NULLIF(SUM(observed_checkin_records) OVER(
           PARTITION BY hospital_id,department_code,arrival_month,weekday_monday_zero,arrival_hour),0),2) AS patient_group_record_share_pct
FROM metrics m
ORDER BY arrival_month,hospital_id,department_code,weekday_monday_zero,arrival_hour,age_group,sex_group,parent_complete;
