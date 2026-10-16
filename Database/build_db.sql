-- ============================================================================
-- team3 MySQL DB 생성·적재 규칙 (build_db.sql)
-- 대상 스키마: team3_medallion (정제 데이터, Silver) / team3_medallion_dq (격리·제외·재정제 기록)
-- 실행 위치: 이 파일이 있는 폴더 (CSV 경로가 data/... 상대 경로)
--   mysql --local-infile=1 -u <계정> -p < build_db.sql
-- 전제: 빈 MySQL 8.x 서버. 서버 설정 local_infile=ON 필요 (SET GLOBAL local_infile = 1;)
-- CSV 규칙: UTF-8, 쉼표, LF, 값은 큰따옴표로 감쌈, NULL 은 따옴표 없는 NULL
-- 테이블 구조는 원래 DB 의 SHOW CREATE TABLE 결과를 그대로 사용한다.
-- 제외: 재정제 실행 로그 3개(reclean_quarantine, reclean_issues, reclean_parent_keys, 합계 약 3.8GB)는 용량 때문에 포함하지 않음
-- ============================================================================
SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;
SET UNIQUE_CHECKS = 0;
CREATE DATABASE IF NOT EXISTS `team3_medallion` CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;
CREATE DATABASE IF NOT EXISTS `team3_medallion_dq` CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;

-- ---------------------------------------------------------------- 1. 테이블 생성
USE `team3_medallion`;
CREATE TABLE IF NOT EXISTS `encounter_services` (
  `encounter_service_id` varchar(32) NOT NULL COMMENT '진료 서비스 상세 ID',
  `encounter_id` varchar(32) NOT NULL COMMENT '진료 ID',
  `line_no` int NOT NULL COMMENT '진료 내 상세 순번',
  `service_version_id` varchar(32) NOT NULL COMMENT '서비스 가격 버전 ID',
  `quantity` int NOT NULL COMMENT '서비스 수량',
  `unit_price` int NOT NULL COMMENT '단가(KRW)',
  `line_amount` int NOT NULL COMMENT '상세 금액(KRW)',
  `source_system` varchar(8) NOT NULL COMMENT '원천 시스템',
  PRIMARY KEY (`encounter_service_id`),
  UNIQUE KEY `uq_service_line` (`encounter_id`,`line_no`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='진료 서비스 상세';

USE `team3_medallion`;
CREATE TABLE IF NOT EXISTS `appointment_events` (
  `event_id` varchar(32) NOT NULL COMMENT '이벤트 ID',
  `appointment_id` varchar(32) NOT NULL COMMENT '예약 ID',
  `event_seq` int NOT NULL COMMENT '예약 내 이벤트 순번',
  `event_at` datetime NOT NULL COMMENT '이벤트 발생 시각',
  `event_type` varchar(16) NOT NULL COMMENT '이벤트 유형',
  `new_status` varchar(16) NOT NULL COMMENT '변경 후 상태',
  `scheduled_at` datetime NOT NULL COMMENT '예약 진료 시각',
  `source_system` varchar(8) NOT NULL COMMENT '원천 시스템',
  PRIMARY KEY (`event_id`),
  UNIQUE KEY `uq_event_seq` (`appointment_id`,`event_seq`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='예약 변경 이벤트';

USE `team3_medallion`;
CREATE TABLE IF NOT EXISTS `payments` (
  `payment_id` varchar(32) NOT NULL COMMENT '거래 ID',
  `encounter_id` varchar(32) NOT NULL COMMENT '진료 ID',
  `transacted_at` datetime NOT NULL COMMENT '거래 시각',
  `transaction_type` varchar(16) NOT NULL COMMENT '거래 유형',
  `amount` int NOT NULL COMMENT '거래 금액(KRW)',
  `payment_method` varchar(16) NOT NULL COMMENT '결제 수단',
  `original_payment_id` varchar(32) DEFAULT NULL COMMENT '원결제 ID',
  `source_system` varchar(8) NOT NULL COMMENT '원천 시스템',
  PRIMARY KEY (`payment_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='결제·환불 거래';

USE `team3_medallion`;
CREATE TABLE IF NOT EXISTS `checkins` (
  `checkin_id` varchar(32) NOT NULL COMMENT '접수 ID',
  `patient_id` varchar(32) NOT NULL COMMENT '가상 환자 ID',
  `session_id` varchar(32) NOT NULL COMMENT '운영 구간 ID',
  `appointment_id` varchar(32) DEFAULT NULL COMMENT '예약 ID',
  `arrival_at` datetime NOT NULL COMMENT '도착 시각',
  `checked_in_at` datetime NOT NULL COMMENT '접수 처리 시각',
  `visit_type` varchar(16) NOT NULL COMMENT '내원 유형',
  `outcome` varchar(16) NOT NULL COMMENT '접수 결과',
  `source_system` varchar(8) NOT NULL COMMENT '원천 시스템',
  PRIMARY KEY (`checkin_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='내원 접수 시도';

USE `team3_medallion`;
CREATE TABLE IF NOT EXISTS `appointments` (
  `appointment_id` varchar(32) NOT NULL COMMENT '예약 ID',
  `patient_id` varchar(32) NOT NULL COMMENT '가상 환자 ID',
  `slot_id` varchar(32) NOT NULL COMMENT '예약 시간대 ID',
  `booked_at` datetime NOT NULL COMMENT '예약 생성 시각',
  `scheduled_at` datetime NOT NULL COMMENT '예약 진료 시각',
  `status` varchar(16) NOT NULL COMMENT '예약 최종 상태',
  `channel` varchar(16) NOT NULL COMMENT '예약 채널',
  `last_event_seq` int NOT NULL COMMENT '최종 이벤트 순번',
  `source_system` varchar(8) NOT NULL COMMENT '원천 시스템',
  PRIMARY KEY (`appointment_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='예약 최종 상태';

USE `team3_medallion`;
CREATE TABLE IF NOT EXISTS `appointment_slots` (
  `slot_id` varchar(32) NOT NULL COMMENT '예약 시간대 ID',
  `session_id` varchar(32) NOT NULL COMMENT '운영 구간 ID',
  `slot_start` datetime NOT NULL COMMENT '시간대 시작 시각',
  `slot_end` datetime NOT NULL COMMENT '시간대 종료 시각',
  `capacity` int NOT NULL COMMENT '정원',
  `source_system` varchar(8) NOT NULL COMMENT '원천 시스템',
  PRIMARY KEY (`slot_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='예약 시간대';

USE `team3_medallion`;
CREATE TABLE IF NOT EXISTS `encounters` (
  `encounter_id` varchar(32) NOT NULL COMMENT '진료 ID',
  `checkin_id` varchar(32) NOT NULL COMMENT '접수 ID',
  `started_at` datetime NOT NULL COMMENT '진료 시작 시각',
  `ended_at` datetime NOT NULL COMMENT '진료 종료 시각',
  `gross_charge` int NOT NULL COMMENT '총 청구액(KRW)',
  `authorized_refund` int NOT NULL COMMENT '승인 환불액(KRW)',
  `net_charge` int NOT NULL COMMENT '최종 청구액(KRW)',
  `source_system` varchar(8) NOT NULL COMMENT '원천 시스템',
  PRIMARY KEY (`encounter_id`),
  UNIQUE KEY `uq_enc_checkin` (`checkin_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='완료 진료';

USE `team3_medallion`;
CREATE TABLE IF NOT EXISTS `clinic_sessions` (
  `session_id` varchar(32) NOT NULL COMMENT '운영 구간 ID',
  `hospital_department_id` varchar(32) NOT NULL COMMENT '병원별 진료과 ID',
  `assignment_id` varchar(32) NOT NULL COMMENT '의사 배치 ID',
  `session_start` datetime NOT NULL COMMENT '운영 시작 시각',
  `session_end` datetime NOT NULL COMMENT '운영 종료 시각',
  `capacity` int NOT NULL COMMENT '정원',
  `session_status` varchar(16) NOT NULL COMMENT '운영 상태',
  `source_system` varchar(8) NOT NULL COMMENT '원천 시스템',
  PRIMARY KEY (`session_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='진료 운영 구간';

USE `team3_medallion`;
CREATE TABLE IF NOT EXISTS `patients` (
  `patient_id` varchar(32) NOT NULL COMMENT '가상 환자 ID',
  `birth_date` date NOT NULL COMMENT '생년월일',
  `sex_code` char(1) NOT NULL COMMENT '성별 코드',
  `region_code` varchar(8) NOT NULL COMMENT '합성 지역 코드',
  `registered_at` datetime NOT NULL COMMENT '최초 등록 시각',
  `active_yn` char(1) NOT NULL COMMENT '활성 여부',
  `source_system` varchar(8) NOT NULL COMMENT '원천 시스템',
  PRIMARY KEY (`patient_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='가상 환자 기준정보';

USE `team3_medallion`;
CREATE TABLE IF NOT EXISTS `doctor_assignments` (
  `assignment_id` varchar(32) NOT NULL COMMENT '의사 배치 ID',
  `doctor_id` varchar(32) NOT NULL COMMENT '의사 ID',
  `hospital_department_id` varchar(32) NOT NULL COMMENT '병원별 진료과 ID',
  `valid_from` date NOT NULL COMMENT '유효 시작일',
  `valid_to` date NOT NULL COMMENT '유효 종료일',
  `allocation_pct` int NOT NULL COMMENT '배치 비율(%)',
  `source_system` varchar(8) NOT NULL COMMENT '원천 시스템',
  PRIMARY KEY (`assignment_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='의사 배치 이력';

USE `team3_medallion`;
CREATE TABLE IF NOT EXISTS `doctors` (
  `doctor_id` varchar(32) NOT NULL COMMENT '의사 ID',
  `doctor_name` varchar(100) NOT NULL COMMENT '의사 표시명',
  `department_code` varchar(32) NOT NULL COMMENT '진료과 코드',
  `hire_date` date NOT NULL COMMENT '채용일',
  `active_yn` char(1) NOT NULL COMMENT '활성 여부',
  `source_system` varchar(8) NOT NULL COMMENT '원천 시스템',
  PRIMARY KEY (`doctor_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='의사 기준정보';

USE `team3_medallion`;
CREATE TABLE IF NOT EXISTS `hospital_departments` (
  `hospital_department_id` varchar(32) NOT NULL COMMENT '병원별 진료과 ID',
  `hospital_id` varchar(32) NOT NULL COMMENT '병원 ID',
  `department_code` varchar(32) NOT NULL COMMENT '진료과 코드',
  `active_yn` char(1) NOT NULL COMMENT '활성 여부',
  `source_system` varchar(8) NOT NULL COMMENT '원천 시스템',
  PRIMARY KEY (`hospital_department_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='병원별 운영 진료과';

USE `team3_medallion`;
CREATE TABLE IF NOT EXISTS `hospitals` (
  `hospital_id` varchar(32) NOT NULL COMMENT '병원 ID',
  `hospital_name` varchar(100) NOT NULL COMMENT '병원명',
  `region_code` varchar(8) NOT NULL COMMENT '합성 지역 코드',
  `hospital_type` varchar(16) NOT NULL COMMENT '병원 유형',
  `opened_date` date NOT NULL COMMENT '개설일',
  `active_yn` char(1) NOT NULL COMMENT '활성 여부',
  `source_system` varchar(8) NOT NULL COMMENT '원천 시스템',
  PRIMARY KEY (`hospital_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='병원 기준정보';

USE `team3_medallion`;
CREATE TABLE IF NOT EXISTS `service_catalog` (
  `service_version_id` varchar(32) NOT NULL COMMENT '서비스 가격 버전 ID',
  `service_code` varchar(32) NOT NULL COMMENT '합성 서비스 코드',
  `service_name` varchar(100) NOT NULL COMMENT '합성 서비스명',
  `service_category` varchar(16) NOT NULL COMMENT '서비스 분류',
  `valid_from` date NOT NULL COMMENT '유효 시작일',
  `valid_to` date NOT NULL COMMENT '유효 종료일',
  `unit_price` int NOT NULL COMMENT '단가(KRW)',
  `source_system` varchar(8) NOT NULL COMMENT '원천 시스템',
  PRIMARY KEY (`service_version_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='서비스 가격 버전';

USE `team3_medallion`;
CREATE TABLE IF NOT EXISTS `departments` (
  `department_code` varchar(32) NOT NULL COMMENT '진료과 코드',
  `department_name` varchar(100) NOT NULL COMMENT '진료과명',
  `source_system` varchar(8) NOT NULL COMMENT '원천 시스템',
  PRIMARY KEY (`department_code`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='진료과 표준 코드';

USE `team3_medallion`;
CREATE TABLE IF NOT EXISTS `code_dictionary` (
  `dictionary_id` varchar(32) NOT NULL COMMENT '사전 항목 ID',
  `domain` varchar(32) NOT NULL COMMENT '코드 도메인',
  `standard_code` varchar(32) NOT NULL COMMENT '표준 코드',
  `label` varchar(100) NOT NULL COMMENT '코드 표시명',
  `dictionary_version` varchar(16) NOT NULL COMMENT '사전 버전',
  `source_system` varchar(8) NOT NULL COMMENT '원천 시스템',
  PRIMARY KEY (`dictionary_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='표준 코드 사전';

USE `team3_medallion`;
CREATE TABLE IF NOT EXISTS `legacy_code_mappings` (
  `mapping_id` varchar(32) NOT NULL COMMENT '매핑 ID',
  `domain` varchar(32) NOT NULL COMMENT '코드 도메인',
  `raw_code` varchar(32) NOT NULL COMMENT '원천 표기',
  `standard_code` varchar(32) NOT NULL COMMENT '표준 코드',
  `mapping_version` varchar(16) NOT NULL COMMENT '매핑 버전',
  `source_system` varchar(8) NOT NULL COMMENT '원천 시스템',
  PRIMARY KEY (`mapping_id`),
  UNIQUE KEY `uq_mapping` (`source_system`,`domain`,`raw_code`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='원천 코드 매핑';

USE `team3_medallion_dq`;
CREATE TABLE IF NOT EXISTS `checkins_quarantine` (
  `checkin_id` text,
  `patient_id` text,
  `session_id` text,
  `appointment_id` text,
  `arrival_at` text,
  `checked_in_at` text,
  `visit_type` text,
  `outcome` text,
  `source_system` text,
  `_src_file` varchar(100) DEFAULT NULL,
  `_src_line` int DEFAULT NULL,
  `reason_codes` text,
  `reason_primary` varchar(100) DEFAULT NULL,
  `quarantine_type` varchar(8) DEFAULT NULL COMMENT '직접/연쇄',
  `repair_hint` text
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

USE `team3_medallion_dq`;
CREATE TABLE IF NOT EXISTS `reclean_finance_before` (
  `encounter_id` varchar(32) NOT NULL,
  `gross_charge` bigint DEFAULT NULL,
  `authorized_refund` bigint DEFAULT NULL,
  `net_charge` bigint DEFAULT NULL,
  `service_count` bigint DEFAULT NULL,
  `service_total` decimal(30,0) DEFAULT NULL,
  `payment_total` decimal(30,0) DEFAULT NULL,
  `refund_total` decimal(30,0) DEFAULT NULL,
  `mismatch` tinyint NOT NULL,
  PRIMARY KEY (`encounter_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

USE `team3_medallion_dq`;
CREATE TABLE IF NOT EXISTS `appointment_slots_quarantine` (
  `slot_id` text,
  `session_id` text,
  `slot_start` text,
  `slot_end` text,
  `capacity` text,
  `source_system` text,
  `_src_file` varchar(100) DEFAULT NULL,
  `_src_line` int DEFAULT NULL,
  `reason_codes` text,
  `reason_primary` varchar(100) DEFAULT NULL,
  `quarantine_type` varchar(8) DEFAULT NULL COMMENT '직접/연쇄',
  `repair_hint` text
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

USE `team3_medallion_dq`;
CREATE TABLE IF NOT EXISTS `encounter_services` (
  `encounter_service_id` varchar(32) NOT NULL COMMENT '진료 서비스 상세 ID',
  `encounter_id` varchar(32) NOT NULL COMMENT '진료 ID',
  `line_no` int NOT NULL COMMENT '진료 내 상세 순번',
  `service_version_id` varchar(32) NOT NULL COMMENT '서비스 가격 버전 ID',
  `quantity` int NOT NULL COMMENT '서비스 수량',
  `unit_price` int NOT NULL COMMENT '단가(KRW)',
  `line_amount` int NOT NULL COMMENT '상세 금액(KRW)',
  `source_system` varchar(8) NOT NULL COMMENT '원천 시스템',
  PRIMARY KEY (`encounter_service_id`),
  UNIQUE KEY `uq_service_line` (`encounter_id`,`line_no`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='진료 서비스 상세';

USE `team3_medallion_dq`;
CREATE TABLE IF NOT EXISTS `reclean_exceptions` (
  `exception_id` bigint NOT NULL AUTO_INCREMENT,
  `rule_code` varchar(128) NOT NULL,
  `table_name` varchar(64) NOT NULL,
  `row_key` varchar(128) DEFAULT NULL,
  `detail` json NOT NULL,
  PRIMARY KEY (`exception_id`),
  KEY `rule_lookup` (`rule_code`)
) ENGINE=InnoDB AUTO_INCREMENT=458746 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

USE `team3_medallion_dq`;
CREATE TABLE IF NOT EXISTS `reclean_repairs` (
  `table_name` varchar(64) NOT NULL,
  `row_key` varchar(32) NOT NULL,
  `source_key` varchar(32) NOT NULL,
  `original_row` json NOT NULL,
  `normalized_row` json NOT NULL,
  `basis` varchar(500) NOT NULL,
  PRIMARY KEY (`table_name`,`row_key`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

USE `team3_medallion_dq`;
CREATE TABLE IF NOT EXISTS `encounters` (
  `encounter_id` varchar(32) NOT NULL COMMENT '진료 ID',
  `checkin_id` varchar(32) NOT NULL COMMENT '접수 ID',
  `started_at` datetime NOT NULL COMMENT '진료 시작 시각',
  `ended_at` datetime NOT NULL COMMENT '진료 종료 시각',
  `gross_charge` int NOT NULL COMMENT '총 청구액(KRW)',
  `authorized_refund` int NOT NULL COMMENT '승인 환불액(KRW)',
  `net_charge` int NOT NULL COMMENT '최종 청구액(KRW)',
  `source_system` varchar(8) NOT NULL COMMENT '원천 시스템',
  PRIMARY KEY (`encounter_id`),
  UNIQUE KEY `uq_enc_checkin` (`checkin_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='완료 진료';

USE `team3_medallion_dq`;
CREATE TABLE IF NOT EXISTS `payments_quarantine` (
  `_row_id` text COLLATE utf8mb4_bin,
  `payment_id` text COLLATE utf8mb4_bin,
  `encounter_id` text COLLATE utf8mb4_bin,
  `transacted_at` text COLLATE utf8mb4_bin,
  `transaction_type` text COLLATE utf8mb4_bin,
  `amount` text COLLATE utf8mb4_bin,
  `payment_method` text COLLATE utf8mb4_bin,
  `original_payment_id` text COLLATE utf8mb4_bin,
  `source_system` text COLLATE utf8mb4_bin,
  `_csv_line` text COLLATE utf8mb4_bin,
  `_file` text COLLATE utf8mb4_bin,
  `_issues` text COLLATE utf8mb4_bin
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin;

USE `team3_medallion_dq`;
CREATE TABLE IF NOT EXISTS `checkins_dual_pairs` (
  `pair_no` int DEFAULT NULL,
  `checkin_id` varchar(32) DEFAULT NULL,
  `patient_id` varchar(32) DEFAULT NULL,
  `session_id` varchar(32) DEFAULT NULL,
  `arrival_at` datetime DEFAULT NULL,
  `visit_type` varchar(16) DEFAULT NULL,
  `outcome` varchar(16) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='이중 접수 의심 쌍(참고용)';

USE `team3_medallion_dq`;
CREATE TABLE IF NOT EXISTS `clinic_sessions_quarantine` (
  `session_id` text,
  `hospital_department_id` text,
  `assignment_id` text,
  `session_start` text,
  `session_end` text,
  `capacity` text,
  `session_status` text,
  `source_system` text,
  `_src_file` varchar(100) DEFAULT NULL,
  `_src_line` int DEFAULT NULL,
  `reason_codes` text,
  `reason_primary` varchar(100) DEFAULT NULL,
  `quarantine_type` varchar(8) DEFAULT NULL COMMENT '직접/연쇄',
  `repair_hint` text
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

USE `team3_medallion_dq`;
CREATE TABLE IF NOT EXISTS `reclean_excluded_mirrors` (
  `table_name` varchar(64) NOT NULL,
  `row_key` varchar(32) NOT NULL,
  `legacy_dq_table` varchar(64) NOT NULL,
  `original_row` json NOT NULL,
  `reason` varchar(500) NOT NULL,
  PRIMARY KEY (`table_name`,`row_key`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

USE `team3_medallion_dq`;
CREATE TABLE IF NOT EXISTS `checkins_excluded` (
  `checkin_id` text,
  `patient_id` text,
  `session_id` text,
  `appointment_id` text,
  `arrival_at` text,
  `checked_in_at` text,
  `visit_type` text,
  `outcome` text,
  `source_system` text,
  `_src_file` varchar(100) DEFAULT NULL,
  `_src_line` int DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='완전 중복 제외 행';

USE `team3_medallion_dq`;
CREATE TABLE IF NOT EXISTS `payments_excluded` (
  `_row_id` text COLLATE utf8mb4_bin,
  `payment_id` text COLLATE utf8mb4_bin,
  `encounter_id` text COLLATE utf8mb4_bin,
  `transacted_at` text COLLATE utf8mb4_bin,
  `transaction_type` text COLLATE utf8mb4_bin,
  `amount` text COLLATE utf8mb4_bin,
  `payment_method` text COLLATE utf8mb4_bin,
  `original_payment_id` text COLLATE utf8mb4_bin,
  `source_system` text COLLATE utf8mb4_bin,
  `_csv_line` text COLLATE utf8mb4_bin,
  `_file` text COLLATE utf8mb4_bin,
  `_reason` text COLLATE utf8mb4_bin
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin;

USE `team3_medallion_dq`;
CREATE TABLE IF NOT EXISTS `doctor_assignments_quarantine` (
  `assignment_id` text,
  `doctor_id` text,
  `hospital_department_id` text,
  `valid_from` text,
  `valid_to` text,
  `allocation_pct` text,
  `source_system` text,
  `_src_file` varchar(100) DEFAULT NULL,
  `_src_line` int DEFAULT NULL,
  `reason_codes` text,
  `reason_primary` varchar(100) DEFAULT NULL,
  `quarantine_type` varchar(8) DEFAULT NULL COMMENT '직접/연쇄',
  `repair_hint` text
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

USE `team3_medallion_dq`;
CREATE TABLE IF NOT EXISTS `doctors_quarantine` (
  `doctor_id` text,
  `doctor_name` text,
  `department_code` text,
  `hire_date` text,
  `active_yn` text,
  `source_system` text,
  `_src_file` varchar(100) DEFAULT NULL,
  `_src_line` int DEFAULT NULL,
  `reason_codes` text,
  `reason_primary` varchar(100) DEFAULT NULL,
  `quarantine_type` varchar(8) DEFAULT NULL COMMENT '직접/연쇄',
  `repair_hint` text
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

USE `team3_medallion_dq`;
CREATE TABLE IF NOT EXISTS `departments_excluded` (
  `_row_id` text COLLATE utf8mb4_bin,
  `department_code` text COLLATE utf8mb4_bin,
  `department_name` text COLLATE utf8mb4_bin,
  `source_system` text COLLATE utf8mb4_bin,
  `_csv_line` text COLLATE utf8mb4_bin,
  `_file` text COLLATE utf8mb4_bin,
  `_reason` text COLLATE utf8mb4_bin
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin;

USE `team3_medallion_dq`;
CREATE TABLE IF NOT EXISTS `departments_quarantine` (
  `_row_id` text COLLATE utf8mb4_bin,
  `department_code` text COLLATE utf8mb4_bin,
  `department_name` text COLLATE utf8mb4_bin,
  `source_system` text COLLATE utf8mb4_bin,
  `_csv_line` text COLLATE utf8mb4_bin,
  `_file` text COLLATE utf8mb4_bin,
  `_issues` text COLLATE utf8mb4_bin
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin;

USE `team3_medallion_dq`;
CREATE TABLE IF NOT EXISTS `doctor_assignments_excluded` (
  `assignment_id` text,
  `doctor_id` text,
  `hospital_department_id` text,
  `valid_from` text,
  `valid_to` text,
  `allocation_pct` text,
  `source_system` text,
  `_src_file` varchar(100) DEFAULT NULL,
  `_src_line` int DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='완전 중복 제외 행';

USE `team3_medallion_dq`;
CREATE TABLE IF NOT EXISTS `doctors_excluded` (
  `doctor_id` text,
  `doctor_name` text,
  `department_code` text,
  `hire_date` text,
  `active_yn` text,
  `source_system` text,
  `_src_file` varchar(100) DEFAULT NULL,
  `_src_line` int DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='완전 중복 제외 행';

USE `team3_medallion_dq`;
CREATE TABLE IF NOT EXISTS `hospital_departments_excluded` (
  `_row_id` text COLLATE utf8mb4_bin,
  `hospital_department_id` text COLLATE utf8mb4_bin,
  `hospital_id` text COLLATE utf8mb4_bin,
  `department_code` text COLLATE utf8mb4_bin,
  `active_yn` text COLLATE utf8mb4_bin,
  `source_system` text COLLATE utf8mb4_bin,
  `_csv_line` text COLLATE utf8mb4_bin,
  `_file` text COLLATE utf8mb4_bin,
  `_reason` text COLLATE utf8mb4_bin
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin;

USE `team3_medallion_dq`;
CREATE TABLE IF NOT EXISTS `hospital_departments_quarantine` (
  `_row_id` text COLLATE utf8mb4_bin,
  `hospital_department_id` text COLLATE utf8mb4_bin,
  `hospital_id` text COLLATE utf8mb4_bin,
  `department_code` text COLLATE utf8mb4_bin,
  `active_yn` text COLLATE utf8mb4_bin,
  `source_system` text COLLATE utf8mb4_bin,
  `_csv_line` text COLLATE utf8mb4_bin,
  `_file` text COLLATE utf8mb4_bin,
  `_issues` text COLLATE utf8mb4_bin
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin;

USE `team3_medallion_dq`;
CREATE TABLE IF NOT EXISTS `clinic_sessions_excluded` (
  `session_id` text,
  `hospital_department_id` text,
  `assignment_id` text,
  `session_start` text,
  `session_end` text,
  `capacity` text,
  `session_status` text,
  `source_system` text,
  `_src_file` varchar(100) DEFAULT NULL,
  `_src_line` int DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='완전 중복 제외 행';

USE `team3_medallion_dq`;
CREATE TABLE IF NOT EXISTS `appointment_slots_excluded` (
  `slot_id` text,
  `session_id` text,
  `slot_start` text,
  `slot_end` text,
  `capacity` text,
  `source_system` text,
  `_src_file` varchar(100) DEFAULT NULL,
  `_src_line` int DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='완전 중복 제외 행';

USE `team3_medallion_dq`;
CREATE TABLE IF NOT EXISTS `cross_recovery_log_20261015` (
  `run_id` char(36) NOT NULL,
  `table_name` varchar(64) NOT NULL,
  `row_pk` varchar(32) NOT NULL,
  `action_name` varchar(32) NOT NULL,
  `row_before` json DEFAULT NULL,
  `row_after` json NOT NULL,
  `evidence` varchar(1000) NOT NULL,
  `logged_at` datetime(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  PRIMARY KEY (`run_id`,`table_name`,`row_pk`,`action_name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- ---------------------------------------------------------------- 2. CSV 적재
LOAD DATA LOCAL INFILE 'data/team3_medallion/encounter_services_part01.csv' INTO TABLE `team3_medallion`.`encounter_services` CHARACTER SET utf8mb4
  FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '"' ESCAPED BY '' LINES TERMINATED BY '\n' IGNORE 1 LINES;
LOAD DATA LOCAL INFILE 'data/team3_medallion/encounter_services_part02.csv' INTO TABLE `team3_medallion`.`encounter_services` CHARACTER SET utf8mb4
  FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '"' ESCAPED BY '' LINES TERMINATED BY '\n' IGNORE 1 LINES;
LOAD DATA LOCAL INFILE 'data/team3_medallion/appointment_events_part01.csv' INTO TABLE `team3_medallion`.`appointment_events` CHARACTER SET utf8mb4
  FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '"' ESCAPED BY '' LINES TERMINATED BY '\n' IGNORE 1 LINES;
LOAD DATA LOCAL INFILE 'data/team3_medallion/appointment_events_part02.csv' INTO TABLE `team3_medallion`.`appointment_events` CHARACTER SET utf8mb4
  FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '"' ESCAPED BY '' LINES TERMINATED BY '\n' IGNORE 1 LINES;
LOAD DATA LOCAL INFILE 'data/team3_medallion/payments.csv' INTO TABLE `team3_medallion`.`payments` CHARACTER SET utf8mb4
  FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '"' ESCAPED BY '' LINES TERMINATED BY '\n' IGNORE 1 LINES;
LOAD DATA LOCAL INFILE 'data/team3_medallion/checkins_part01.csv' INTO TABLE `team3_medallion`.`checkins` CHARACTER SET utf8mb4
  FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '"' ESCAPED BY '' LINES TERMINATED BY '\n' IGNORE 1 LINES;
LOAD DATA LOCAL INFILE 'data/team3_medallion/checkins_part02.csv' INTO TABLE `team3_medallion`.`checkins` CHARACTER SET utf8mb4
  FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '"' ESCAPED BY '' LINES TERMINATED BY '\n' IGNORE 1 LINES;
LOAD DATA LOCAL INFILE 'data/team3_medallion/appointments.csv' INTO TABLE `team3_medallion`.`appointments` CHARACTER SET utf8mb4
  FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '"' ESCAPED BY '' LINES TERMINATED BY '\n' IGNORE 1 LINES;
LOAD DATA LOCAL INFILE 'data/team3_medallion/appointment_slots.csv' INTO TABLE `team3_medallion`.`appointment_slots` CHARACTER SET utf8mb4
  FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '"' ESCAPED BY '' LINES TERMINATED BY '\n' IGNORE 1 LINES;
LOAD DATA LOCAL INFILE 'data/team3_medallion/encounters.csv' INTO TABLE `team3_medallion`.`encounters` CHARACTER SET utf8mb4
  FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '"' ESCAPED BY '' LINES TERMINATED BY '\n' IGNORE 1 LINES;
LOAD DATA LOCAL INFILE 'data/team3_medallion/clinic_sessions.csv' INTO TABLE `team3_medallion`.`clinic_sessions` CHARACTER SET utf8mb4
  FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '"' ESCAPED BY '' LINES TERMINATED BY '\n' IGNORE 1 LINES;
LOAD DATA LOCAL INFILE 'data/team3_medallion/patients.csv' INTO TABLE `team3_medallion`.`patients` CHARACTER SET utf8mb4
  FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '"' ESCAPED BY '' LINES TERMINATED BY '\n' IGNORE 1 LINES;
LOAD DATA LOCAL INFILE 'data/team3_medallion/doctor_assignments.csv' INTO TABLE `team3_medallion`.`doctor_assignments` CHARACTER SET utf8mb4
  FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '"' ESCAPED BY '' LINES TERMINATED BY '\n' IGNORE 1 LINES;
LOAD DATA LOCAL INFILE 'data/team3_medallion/doctors.csv' INTO TABLE `team3_medallion`.`doctors` CHARACTER SET utf8mb4
  FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '"' ESCAPED BY '' LINES TERMINATED BY '\n' IGNORE 1 LINES;
LOAD DATA LOCAL INFILE 'data/team3_medallion/hospital_departments.csv' INTO TABLE `team3_medallion`.`hospital_departments` CHARACTER SET utf8mb4
  FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '"' ESCAPED BY '' LINES TERMINATED BY '\n' IGNORE 1 LINES;
LOAD DATA LOCAL INFILE 'data/team3_medallion/hospitals.csv' INTO TABLE `team3_medallion`.`hospitals` CHARACTER SET utf8mb4
  FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '"' ESCAPED BY '' LINES TERMINATED BY '\n' IGNORE 1 LINES;
LOAD DATA LOCAL INFILE 'data/team3_medallion/service_catalog.csv' INTO TABLE `team3_medallion`.`service_catalog` CHARACTER SET utf8mb4
  FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '"' ESCAPED BY '' LINES TERMINATED BY '\n' IGNORE 1 LINES;
LOAD DATA LOCAL INFILE 'data/team3_medallion/departments.csv' INTO TABLE `team3_medallion`.`departments` CHARACTER SET utf8mb4
  FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '"' ESCAPED BY '' LINES TERMINATED BY '\n' IGNORE 1 LINES;
LOAD DATA LOCAL INFILE 'data/team3_medallion/code_dictionary.csv' INTO TABLE `team3_medallion`.`code_dictionary` CHARACTER SET utf8mb4
  FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '"' ESCAPED BY '' LINES TERMINATED BY '\n' IGNORE 1 LINES;
LOAD DATA LOCAL INFILE 'data/team3_medallion/legacy_code_mappings.csv' INTO TABLE `team3_medallion`.`legacy_code_mappings` CHARACTER SET utf8mb4
  FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '"' ESCAPED BY '' LINES TERMINATED BY '\n' IGNORE 1 LINES;
LOAD DATA LOCAL INFILE 'data/team3_medallion_dq/checkins_quarantine.csv' INTO TABLE `team3_medallion_dq`.`checkins_quarantine` CHARACTER SET utf8mb4
  FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '"' ESCAPED BY '' LINES TERMINATED BY '\n' IGNORE 1 LINES;
LOAD DATA LOCAL INFILE 'data/team3_medallion_dq/reclean_finance_before.csv' INTO TABLE `team3_medallion_dq`.`reclean_finance_before` CHARACTER SET utf8mb4
  FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '"' ESCAPED BY '' LINES TERMINATED BY '\n' IGNORE 1 LINES;
LOAD DATA LOCAL INFILE 'data/team3_medallion_dq/appointment_slots_quarantine.csv' INTO TABLE `team3_medallion_dq`.`appointment_slots_quarantine` CHARACTER SET utf8mb4
  FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '"' ESCAPED BY '' LINES TERMINATED BY '\n' IGNORE 1 LINES;
LOAD DATA LOCAL INFILE 'data/team3_medallion_dq/encounter_services.csv' INTO TABLE `team3_medallion_dq`.`encounter_services` CHARACTER SET utf8mb4
  FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '"' ESCAPED BY '' LINES TERMINATED BY '\n' IGNORE 1 LINES;
LOAD DATA LOCAL INFILE 'data/team3_medallion_dq/reclean_exceptions.csv' INTO TABLE `team3_medallion_dq`.`reclean_exceptions` CHARACTER SET utf8mb4
  FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '"' ESCAPED BY '' LINES TERMINATED BY '\n' IGNORE 1 LINES;
LOAD DATA LOCAL INFILE 'data/team3_medallion_dq/reclean_repairs.csv' INTO TABLE `team3_medallion_dq`.`reclean_repairs` CHARACTER SET utf8mb4
  FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '"' ESCAPED BY '' LINES TERMINATED BY '\n' IGNORE 1 LINES;
LOAD DATA LOCAL INFILE 'data/team3_medallion_dq/encounters.csv' INTO TABLE `team3_medallion_dq`.`encounters` CHARACTER SET utf8mb4
  FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '"' ESCAPED BY '' LINES TERMINATED BY '\n' IGNORE 1 LINES;
LOAD DATA LOCAL INFILE 'data/team3_medallion_dq/payments_quarantine.csv' INTO TABLE `team3_medallion_dq`.`payments_quarantine` CHARACTER SET utf8mb4
  FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '"' ESCAPED BY '' LINES TERMINATED BY '\n' IGNORE 1 LINES;
LOAD DATA LOCAL INFILE 'data/team3_medallion_dq/checkins_dual_pairs.csv' INTO TABLE `team3_medallion_dq`.`checkins_dual_pairs` CHARACTER SET utf8mb4
  FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '"' ESCAPED BY '' LINES TERMINATED BY '\n' IGNORE 1 LINES;
LOAD DATA LOCAL INFILE 'data/team3_medallion_dq/clinic_sessions_quarantine.csv' INTO TABLE `team3_medallion_dq`.`clinic_sessions_quarantine` CHARACTER SET utf8mb4
  FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '"' ESCAPED BY '' LINES TERMINATED BY '\n' IGNORE 1 LINES;
LOAD DATA LOCAL INFILE 'data/team3_medallion_dq/reclean_excluded_mirrors.csv' INTO TABLE `team3_medallion_dq`.`reclean_excluded_mirrors` CHARACTER SET utf8mb4
  FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '"' ESCAPED BY '' LINES TERMINATED BY '\n' IGNORE 1 LINES;
LOAD DATA LOCAL INFILE 'data/team3_medallion_dq/checkins_excluded.csv' INTO TABLE `team3_medallion_dq`.`checkins_excluded` CHARACTER SET utf8mb4
  FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '"' ESCAPED BY '' LINES TERMINATED BY '\n' IGNORE 1 LINES;
LOAD DATA LOCAL INFILE 'data/team3_medallion_dq/payments_excluded.csv' INTO TABLE `team3_medallion_dq`.`payments_excluded` CHARACTER SET utf8mb4
  FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '"' ESCAPED BY '' LINES TERMINATED BY '\n' IGNORE 1 LINES;
LOAD DATA LOCAL INFILE 'data/team3_medallion_dq/doctor_assignments_quarantine.csv' INTO TABLE `team3_medallion_dq`.`doctor_assignments_quarantine` CHARACTER SET utf8mb4
  FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '"' ESCAPED BY '' LINES TERMINATED BY '\n' IGNORE 1 LINES;
LOAD DATA LOCAL INFILE 'data/team3_medallion_dq/doctors_quarantine.csv' INTO TABLE `team3_medallion_dq`.`doctors_quarantine` CHARACTER SET utf8mb4
  FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '"' ESCAPED BY '' LINES TERMINATED BY '\n' IGNORE 1 LINES;
LOAD DATA LOCAL INFILE 'data/team3_medallion_dq/departments_excluded.csv' INTO TABLE `team3_medallion_dq`.`departments_excluded` CHARACTER SET utf8mb4
  FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '"' ESCAPED BY '' LINES TERMINATED BY '\n' IGNORE 1 LINES;
LOAD DATA LOCAL INFILE 'data/team3_medallion_dq/departments_quarantine.csv' INTO TABLE `team3_medallion_dq`.`departments_quarantine` CHARACTER SET utf8mb4
  FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '"' ESCAPED BY '' LINES TERMINATED BY '\n' IGNORE 1 LINES;
LOAD DATA LOCAL INFILE 'data/team3_medallion_dq/doctor_assignments_excluded.csv' INTO TABLE `team3_medallion_dq`.`doctor_assignments_excluded` CHARACTER SET utf8mb4
  FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '"' ESCAPED BY '' LINES TERMINATED BY '\n' IGNORE 1 LINES;
LOAD DATA LOCAL INFILE 'data/team3_medallion_dq/doctors_excluded.csv' INTO TABLE `team3_medallion_dq`.`doctors_excluded` CHARACTER SET utf8mb4
  FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '"' ESCAPED BY '' LINES TERMINATED BY '\n' IGNORE 1 LINES;
LOAD DATA LOCAL INFILE 'data/team3_medallion_dq/hospital_departments_excluded.csv' INTO TABLE `team3_medallion_dq`.`hospital_departments_excluded` CHARACTER SET utf8mb4
  FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '"' ESCAPED BY '' LINES TERMINATED BY '\n' IGNORE 1 LINES;
LOAD DATA LOCAL INFILE 'data/team3_medallion_dq/hospital_departments_quarantine.csv' INTO TABLE `team3_medallion_dq`.`hospital_departments_quarantine` CHARACTER SET utf8mb4
  FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '"' ESCAPED BY '' LINES TERMINATED BY '\n' IGNORE 1 LINES;
LOAD DATA LOCAL INFILE 'data/team3_medallion_dq/clinic_sessions_excluded.csv' INTO TABLE `team3_medallion_dq`.`clinic_sessions_excluded` CHARACTER SET utf8mb4
  FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '"' ESCAPED BY '' LINES TERMINATED BY '\n' IGNORE 1 LINES;
LOAD DATA LOCAL INFILE 'data/team3_medallion_dq/appointment_slots_excluded.csv' INTO TABLE `team3_medallion_dq`.`appointment_slots_excluded` CHARACTER SET utf8mb4
  FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '"' ESCAPED BY '' LINES TERMINATED BY '\n' IGNORE 1 LINES;
LOAD DATA LOCAL INFILE 'data/team3_medallion_dq/cross_recovery_log_20261015.csv' INTO TABLE `team3_medallion_dq`.`cross_recovery_log_20261015` CHARACTER SET utf8mb4
  FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '"' ESCAPED BY '' LINES TERMINATED BY '\n' IGNORE 1 LINES;

-- ---------------------------------------------------------------- 3. 뷰 생성 (데이터 없음, 다른 테이블에서 계산)
USE `team3_medallion`;
CREATE OR REPLACE ALGORITHM=UNDEFINED VIEW `team3_medallion`.`baek_silver_encounter_context` AS select `e`.`encounter_id` AS `encounter_id`,`e`.`checkin_id` AS `checkin_id`,`e`.`started_at` AS `started_at`,`e`.`ended_at` AS `ended_at`,`e`.`gross_charge` AS `gross_charge`,`e`.`authorized_refund` AS `authorized_refund`,`e`.`net_charge` AS `net_charge`,`e`.`source_system` AS `source_system`,`c`.`checkin_id` AS `matched_checkin_id`,`s`.`session_id` AS `matched_session_id`,`hd`.`hospital_department_id` AS `matched_hospital_department_id`,`h`.`hospital_id` AS `matched_hospital_id`,`d`.`department_code` AS `matched_department_code`,`h`.`hospital_name` AS `hospital_name`,`d`.`department_name` AS `department_name`,(case when ((`h`.`hospital_id` is not null) and regexp_like(`h`.`hospital_id`,'^HOS_[0-9]{9}$','c')) then `h`.`hospital_id` else '__UNCLASSIFIED__' end) AS `hospital_group`,coalesce(`d`.`department_code`,'__UNCLASSIFIED__') AS `department_group`,coalesce(date_format(`e`.`started_at`,'%Y-%m'),'__UNCLASSIFIED__') AS `treatment_month`,(case when (`c`.`checkin_id` is null) then 'MISSING_CHECKIN' when (`s`.`session_id` is null) then 'MISSING_SESSION' when (`hd`.`hospital_department_id` is null) then 'MISSING_HOSPITAL_DEPARTMENT' when (`h`.`hospital_id` is null) then 'MISSING_HOSPITAL' when (`d`.`department_code` is null) then 'MISSING_DEPARTMENT' when (not(regexp_like(`h`.`hospital_id`,'^HOS_[0-9]{9}$','c'))) then 'INVALID_HOSPITAL_KEY' else 'LINKED' end) AS `context_status` from (((((`team3_medallion`.`encounters` `e` left join `team3_medallion`.`checkins` `c` on((`c`.`checkin_id` = `e`.`checkin_id`))) left join `team3_medallion`.`clinic_sessions` `s` on((`s`.`session_id` = `c`.`session_id`))) left join `team3_medallion`.`hospital_departments` `hd` on((`hd`.`hospital_department_id` = `s`.`hospital_department_id`))) left join `team3_medallion`.`hospitals` `h` on((`h`.`hospital_id` = `hd`.`hospital_id`))) left join `team3_medallion`.`departments` `d` on((`d`.`department_code` = `hd`.`department_code`)));
USE `team3_medallion`;
CREATE OR REPLACE ALGORITHM=UNDEFINED VIEW `team3_medallion`.`baek_silver_payment_totals` AS select `team3_medallion`.`payments`.`encounter_id` AS `encounter_id`,count(0) AS `transaction_rows`,sum((`team3_medallion`.`payments`.`transaction_type` = 'PAYMENT')) AS `payment_rows`,sum((`team3_medallion`.`payments`.`transaction_type` = 'REFUND')) AS `refund_rows`,count(distinct (case when (`team3_medallion`.`payments`.`transaction_type` = 'PAYMENT') then `team3_medallion`.`payments`.`payment_method` end)) AS `method_count`,min((case when (`team3_medallion`.`payments`.`transaction_type` = 'PAYMENT') then `team3_medallion`.`payments`.`payment_method` end)) AS `single_method_candidate`,sum((case when ((`team3_medallion`.`payments`.`transaction_type` = 'PAYMENT') and (`team3_medallion`.`payments`.`amount` > 0)) then `team3_medallion`.`payments`.`amount` else 0 end)) AS `paid_amount`,sum((case when ((`team3_medallion`.`payments`.`transaction_type` = 'REFUND') and (`team3_medallion`.`payments`.`amount` > 0)) then `team3_medallion`.`payments`.`amount` else 0 end)) AS `refunded_amount`,sum((case when ((`team3_medallion`.`payments`.`amount` is null) or (`team3_medallion`.`payments`.`amount` <= 0) or (`team3_medallion`.`payments`.`transaction_type` is null) or (cast(`team3_medallion`.`payments`.`transaction_type` as char charset binary) not in ('PAYMENT','REFUND'))) then 1 else 0 end)) AS `invalid_transaction_rows`,min((case when (`team3_medallion`.`payments`.`transaction_type` = 'PAYMENT') then `team3_medallion`.`payments`.`transacted_at` end)) AS `first_payment_at`,max((case when (`team3_medallion`.`payments`.`transaction_type` = 'PAYMENT') then `team3_medallion`.`payments`.`transacted_at` end)) AS `last_payment_at`,min(`team3_medallion`.`payments`.`transacted_at`) AS `first_transaction_at`,max(`team3_medallion`.`payments`.`transacted_at`) AS `last_transaction_at`,sum((`team3_medallion`.`payments`.`transacted_at` is null)) AS `missing_transaction_time_rows` from `team3_medallion`.`payments` group by `team3_medallion`.`payments`.`encounter_id`;
USE `team3_medallion`;
CREATE OR REPLACE ALGORITHM=UNDEFINED VIEW `team3_medallion`.`baek_silver_qservice_totals` AS select `team3_medallion_dq`.`encounter_services`.`encounter_id` AS `encounter_id`,count(0) AS `quarantine_service_rows` from `team3_medallion_dq`.`encounter_services` group by `team3_medallion_dq`.`encounter_services`.`encounter_id`;
USE `team3_medallion`;
CREATE OR REPLACE ALGORITHM=UNDEFINED VIEW `team3_medallion`.`baek_silver_quarantine_payment_keys` AS select `q`.`_row_id` AS `_row_id`,`q`.`payment_id` AS `payment_id`,`q`.`encounter_id` AS `encounter_id`,`q`.`transacted_at` AS `transacted_at`,`q`.`transaction_type` AS `transaction_type`,`q`.`amount` AS `amount`,`q`.`payment_method` AS `payment_method`,`q`.`original_payment_id` AS `original_payment_id`,`q`.`source_system` AS `source_system`,`q`.`_csv_line` AS `_csv_line`,`q`.`_file` AS `_file`,`q`.`_issues` AS `_issues`,(case when regexp_like(replace(trim(`q`.`encounter_id`),'-','_'),'^ENC_[0-9]{9}$','c') then replace(trim(`q`.`encounter_id`),'-','_') end) AS `linked_encounter_id`,(case when regexp_like(replace(trim(`q`.`original_payment_id`),'-','_'),'^PAY_[0-9]{9}$','c') then replace(trim(`q`.`original_payment_id`),'-','_') end) AS `linked_original_payment_id` from `team3_medallion_dq`.`payments_quarantine` `q`;
USE `team3_medallion`;
CREATE OR REPLACE ALGORITHM=UNDEFINED VIEW `team3_medallion`.`baek_silver_refund_links` AS select `r`.`payment_id` AS `refund_id`,`r`.`encounter_id` AS `encounter_id`,`r`.`transacted_at` AS `refunded_at`,`r`.`amount` AS `refund_amount`,`r`.`original_payment_id` AS `original_payment_id`,`p`.`payment_id` AS `matched_original_payment_id`,`p`.`payment_method` AS `original_payment_method`,`p`.`amount` AS `original_amount`,`p`.`transacted_at` AS `original_paid_at`,(case when (`p`.`payment_id` is null) then 'MISSING_ORIGINAL' when ((`p`.`transaction_type` is null) or (cast(`p`.`transaction_type` as char charset binary) <> 'PAYMENT')) then 'ORIGINAL_NOT_PAYMENT' when ((`r`.`encounter_id` is null) or (`p`.`encounter_id` is null) or (cast(`r`.`encounter_id` as char charset binary) <> cast(`p`.`encounter_id` as char charset binary))) then 'DIFFERENT_OR_UNKNOWN_ENCOUNTER' when ((`r`.`transacted_at` is null) or (`p`.`transacted_at` is null)) then 'UNKNOWN_TIME' when (`r`.`transacted_at` <= `p`.`transacted_at`) then 'REFUND_NOT_AFTER_PAYMENT' when ((`r`.`amount` is null) or (`p`.`amount` is null) or (`r`.`amount` <= 0) or (`p`.`amount` <= 0) or (`r`.`amount` > `p`.`amount`)) then 'INVALID_AMOUNT' else 'LINK_VALID' end) AS `link_status` from (`team3_medallion`.`payments` `r` left join `team3_medallion`.`payments` `p` on((`p`.`payment_id` = `r`.`original_payment_id`))) where (cast(`r`.`transaction_type` as char charset binary) = 'REFUND');
USE `team3_medallion`;
CREATE OR REPLACE ALGORITHM=UNDEFINED VIEW `team3_medallion`.`baek_silver_service_totals` AS select `es`.`encounter_id` AS `encounter_id`,count(0) AS `service_rows`,sum(`es`.`line_amount`) AS `service_amount`,sum((case when ((`es`.`quantity` is null) or (`es`.`unit_price` is null) or (`es`.`line_amount` is null) or (`es`.`quantity` <= 0) or (`es`.`unit_price` <= 0) or (`es`.`line_amount` <> (`es`.`quantity` * `es`.`unit_price`)) or (`sc`.`service_version_id` is null) or (`sc`.`unit_price` is null) or (`sc`.`unit_price` <= 0) or (`es`.`unit_price` <> `sc`.`unit_price`) or (`sc`.`valid_from` is null) or (`sc`.`valid_to` is null) or (`sc`.`valid_from` > `sc`.`valid_to`) or (`e`.`encounter_id` is null) or (`e`.`started_at` is null) or (cast(`e`.`started_at` as date) < `sc`.`valid_from`) or (cast(`e`.`started_at` as date) > `sc`.`valid_to`)) then 1 else 0 end)) AS `invalid_service_rows` from ((`team3_medallion`.`encounter_services` `es` left join `team3_medallion`.`service_catalog` `sc` on((`sc`.`service_version_id` = `es`.`service_version_id`))) left join `team3_medallion`.`encounters` `e` on((`e`.`encounter_id` = `es`.`encounter_id`))) group by `es`.`encounter_id`;
USE `team3_medallion`;
CREATE OR REPLACE ALGORITHM=UNDEFINED VIEW `team3_medallion`.`baek_gold_original_payment_refunds` AS with `refunds` as (select `team3_medallion`.`baek_silver_refund_links`.`original_payment_id` AS `original_payment_id`,count(0) AS `linked_refund_rows`,sum((`team3_medallion`.`baek_silver_refund_links`.`link_status` = 'LINK_VALID')) AS `valid_link_rows`,sum((case when (`team3_medallion`.`baek_silver_refund_links`.`link_status` = 'LINK_VALID') then `team3_medallion`.`baek_silver_refund_links`.`refund_amount` else 0 end)) AS `valid_link_refund_amount`,sum((`team3_medallion`.`baek_silver_refund_links`.`link_status` <> 'LINK_VALID')) AS `invalid_link_rows`,min((case when (`team3_medallion`.`baek_silver_refund_links`.`link_status` = 'LINK_VALID') then `team3_medallion`.`baek_silver_refund_links`.`refunded_at` end)) AS `first_valid_refund_at` from `team3_medallion`.`baek_silver_refund_links` group by `team3_medallion`.`baek_silver_refund_links`.`original_payment_id`), `dq` as (select `team3_medallion`.`baek_silver_quarantine_payment_keys`.`linked_original_payment_id` AS `linked_original_payment_id`,count(0) AS `quarantine_reference_rows` from `team3_medallion`.`baek_silver_quarantine_payment_keys` where (`team3_medallion`.`baek_silver_quarantine_payment_keys`.`linked_original_payment_id` is not null) group by `team3_medallion`.`baek_silver_quarantine_payment_keys`.`linked_original_payment_id`) select `p`.`payment_id` AS `payment_id`,`p`.`encounter_id` AS `encounter_id`,`p`.`transacted_at` AS `transacted_at`,`p`.`payment_method` AS `payment_method`,`p`.`source_system` AS `source_system`,`p`.`amount` AS `amount`,coalesce(`r`.`linked_refund_rows`,0) AS `linked_refund_rows`,coalesce(`r`.`valid_link_rows`,0) AS `valid_link_rows`,coalesce(`r`.`valid_link_refund_amount`,0) AS `valid_link_refund_amount`,coalesce(`r`.`invalid_link_rows`,0) AS `invalid_link_rows`,(coalesce(`r`.`valid_link_refund_amount`,0) > `p`.`amount`) AS `cumulative_refund_exceeds_original`,coalesce(`dq`.`quarantine_reference_rows`,0) AS `quarantine_reference_rows`,`r`.`first_valid_refund_at` AS `first_valid_refund_at`,timestampdiff(MINUTE,`p`.`transacted_at`,`r`.`first_valid_refund_at`) AS `minutes_to_first_refund`,(case when (`e`.`encounter_id` is null) then 'MISSING_FINAL_ENCOUNTER' else 'LINKED' end) AS `encounter_link_status` from (((`team3_medallion`.`payments` `p` left join `refunds` `r` on((`r`.`original_payment_id` = `p`.`payment_id`))) left join `dq` on((`dq`.`linked_original_payment_id` = `p`.`payment_id`))) left join `team3_medallion`.`encounters` `e` on((`e`.`encounter_id` = `p`.`encounter_id`))) where (cast(`p`.`transaction_type` as char charset binary) = 'PAYMENT');
USE `team3_medallion`;
CREATE OR REPLACE ALGORITHM=UNDEFINED VIEW `team3_medallion`.`baek_silver_qpayment_totals` AS select `team3_medallion`.`baek_silver_quarantine_payment_keys`.`linked_encounter_id` AS `encounter_id`,count(0) AS `quarantine_payment_rows` from `team3_medallion`.`baek_silver_quarantine_payment_keys` where (`team3_medallion`.`baek_silver_quarantine_payment_keys`.`linked_encounter_id` is not null) group by `team3_medallion`.`baek_silver_quarantine_payment_keys`.`linked_encounter_id`;
USE `team3_medallion`;
CREATE OR REPLACE ALGORITHM=UNDEFINED VIEW `team3_medallion`.`baek_gold_encounter_finance` AS select `team3_medallion`.`e`.`encounter_id` AS `encounter_id`,`team3_medallion`.`e`.`checkin_id` AS `checkin_id`,`team3_medallion`.`e`.`started_at` AS `started_at`,`team3_medallion`.`e`.`ended_at` AS `ended_at`,`team3_medallion`.`e`.`gross_charge` AS `gross_charge`,`team3_medallion`.`e`.`authorized_refund` AS `authorized_refund`,`team3_medallion`.`e`.`net_charge` AS `net_charge`,`team3_medallion`.`e`.`source_system` AS `source_system`,`team3_medallion`.`e`.`matched_checkin_id` AS `matched_checkin_id`,`team3_medallion`.`e`.`matched_session_id` AS `matched_session_id`,`team3_medallion`.`e`.`matched_hospital_department_id` AS `matched_hospital_department_id`,`team3_medallion`.`e`.`matched_hospital_id` AS `matched_hospital_id`,`team3_medallion`.`e`.`matched_department_code` AS `matched_department_code`,`team3_medallion`.`e`.`hospital_name` AS `hospital_name`,`team3_medallion`.`e`.`department_name` AS `department_name`,`team3_medallion`.`e`.`hospital_group` AS `hospital_group`,`team3_medallion`.`e`.`department_group` AS `department_group`,`team3_medallion`.`e`.`treatment_month` AS `treatment_month`,`team3_medallion`.`e`.`context_status` AS `context_status`,coalesce(`team3_medallion`.`p`.`transaction_rows`,0) AS `transaction_rows`,coalesce(`team3_medallion`.`p`.`payment_rows`,0) AS `payment_rows`,coalesce(`team3_medallion`.`p`.`refund_rows`,0) AS `refund_rows`,coalesce(`team3_medallion`.`p`.`paid_amount`,0) AS `paid_amount`,coalesce(`team3_medallion`.`p`.`refunded_amount`,0) AS `refunded_amount`,(coalesce(`team3_medallion`.`p`.`paid_amount`,0) - coalesce(`team3_medallion`.`p`.`refunded_amount`,0)) AS `recorded_net_amount`,((coalesce(`team3_medallion`.`p`.`paid_amount`,0) - coalesce(`team3_medallion`.`p`.`refunded_amount`,0)) - `team3_medallion`.`e`.`net_charge`) AS `transaction_gap`,`team3_medallion`.`s`.`service_amount` AS `service_amount`,(`team3_medallion`.`s`.`service_amount` - `team3_medallion`.`e`.`gross_charge`) AS `service_gap`,coalesce(`team3_medallion`.`s`.`service_rows`,0) AS `service_rows`,coalesce(`team3_medallion`.`p`.`invalid_transaction_rows`,0) AS `invalid_transaction_rows`,coalesce(`team3_medallion`.`p`.`missing_transaction_time_rows`,0) AS `missing_transaction_time_rows`,coalesce(`team3_medallion`.`s`.`invalid_service_rows`,0) AS `invalid_service_rows`,coalesce(`team3_medallion`.`qp`.`quarantine_payment_rows`,0) AS `quarantine_payment_rows`,coalesce(`team3_medallion`.`qs`.`quarantine_service_rows`,0) AS `quarantine_service_rows`,`team3_medallion`.`p`.`first_payment_at` AS `first_payment_at`,`team3_medallion`.`p`.`last_payment_at` AS `last_payment_at`,`team3_medallion`.`p`.`first_transaction_at` AS `first_transaction_at`,`team3_medallion`.`p`.`last_transaction_at` AS `last_transaction_at`,timestampdiff(MINUTE,`team3_medallion`.`e`.`ended_at`,`team3_medallion`.`p`.`first_payment_at`) AS `first_payment_minutes_from_end`,(case when (`team3_medallion`.`p`.`method_count` > 1) then 'MIXED' when (`team3_medallion`.`p`.`method_count` = 1) then concat('SINGLE_',`team3_medallion`.`p`.`single_method_candidate`) else 'NO_KNOWN_PAYMENT_METHOD' end) AS `method_bundle`,(case when ((`team3_medallion`.`e`.`net_charge` is null) or (`team3_medallion`.`e`.`gross_charge` is null) or (`team3_medallion`.`e`.`authorized_refund` is null)) then 'UNKNOWN_CHARGE' when ((`team3_medallion`.`e`.`net_charge` <> (`team3_medallion`.`e`.`gross_charge` - `team3_medallion`.`e`.`authorized_refund`)) or (`team3_medallion`.`e`.`authorized_refund` < 0) or (`team3_medallion`.`e`.`authorized_refund` > `team3_medallion`.`e`.`gross_charge`)) then 'INVALID_CHARGE' when ((coalesce(`team3_medallion`.`p`.`invalid_transaction_rows`,0) > 0) or (coalesce(`team3_medallion`.`s`.`invalid_service_rows`,0) > 0)) then 'INVALID_CHILD_VALUES' when (`team3_medallion`.`p`.`transaction_rows` is null) then 'NO_RECORDED_TRANSACTION' when ((`team3_medallion`.`qp`.`quarantine_payment_rows` > 0) or (`team3_medallion`.`qs`.`quarantine_service_rows` > 0)) then 'LINKED_QUARANTINE_PRESENT' when (`team3_medallion`.`s`.`service_rows` is null) then 'NO_RECORDED_SERVICE' when (((`team3_medallion`.`p`.`paid_amount` - `team3_medallion`.`p`.`refunded_amount`) <> `team3_medallion`.`e`.`net_charge`) or (`team3_medallion`.`s`.`service_amount` <> `team3_medallion`.`e`.`gross_charge`)) then 'DIFFERENCE_NO_LINKED_DQ' else 'CURRENT_VALUES_MATCH_NO_LINKED_DQ' end) AS `evidence_status` from ((((`team3_medallion`.`baek_silver_encounter_context` `e` left join `team3_medallion`.`baek_silver_payment_totals` `p` on((`team3_medallion`.`p`.`encounter_id` = `team3_medallion`.`e`.`encounter_id`))) left join `team3_medallion`.`baek_silver_service_totals` `s` on((`team3_medallion`.`s`.`encounter_id` = `team3_medallion`.`e`.`encounter_id`))) left join `team3_medallion`.`baek_silver_qpayment_totals` `qp` on((`team3_medallion`.`qp`.`encounter_id` = `team3_medallion`.`e`.`encounter_id`))) left join `team3_medallion`.`baek_silver_qservice_totals` `qs` on((`team3_medallion`.`qs`.`encounter_id` = `team3_medallion`.`e`.`encounter_id`)));
USE `team3_medallion`;
CREATE OR REPLACE ALGORITHM=UNDEFINED VIEW `team3_medallion`.`baek_gold_collection_topic` AS with `bad_refunds` as (select `team3_medallion`.`baek_silver_refund_links`.`encounter_id` AS `encounter_id`,count(0) AS `invalid_refund_links` from `team3_medallion`.`baek_silver_refund_links` where (`team3_medallion`.`baek_silver_refund_links`.`link_status` <> 'LINK_VALID') group by `team3_medallion`.`baek_silver_refund_links`.`encounter_id`), `excessive` as (select `team3_medallion`.`baek_gold_original_payment_refunds`.`encounter_id` AS `encounter_id`,count(0) AS `excessive_refund_originals` from `team3_medallion`.`baek_gold_original_payment_refunds` where (`team3_medallion`.`baek_gold_original_payment_refunds`.`cumulative_refund_exceeds_original` = 1) group by `team3_medallion`.`baek_gold_original_payment_refunds`.`encounter_id`), `timing` as (select `p`.`encounter_id` AS `encounter_id`,sum((case when ((cast(`p`.`transaction_type` as char charset binary) = 'PAYMENT') and (`p`.`transacted_at` >= `e`.`ended_at`)) then 1 else 0 end)) AS `payments_at_or_after_end`,sum((case when ((cast(`p`.`transaction_type` as char charset binary) = 'PAYMENT') and (`p`.`transacted_at` < `e`.`ended_at`)) then 1 else 0 end)) AS `payments_before_end`,sum((case when (cast(`p`.`transacted_at` as date) <> cast(`e`.`ended_at` as date)) then 1 else 0 end)) AS `different_end_date_transactions` from (`team3_medallion`.`payments` `p` join `team3_medallion`.`encounters` `e` on((`e`.`encounter_id` = `p`.`encounter_id`))) group by `p`.`encounter_id`) select `team3_medallion`.`f`.`encounter_id` AS `encounter_id`,`team3_medallion`.`f`.`checkin_id` AS `checkin_id`,`team3_medallion`.`f`.`started_at` AS `started_at`,`team3_medallion`.`f`.`ended_at` AS `ended_at`,`team3_medallion`.`f`.`gross_charge` AS `gross_charge`,`team3_medallion`.`f`.`authorized_refund` AS `authorized_refund`,`team3_medallion`.`f`.`net_charge` AS `net_charge`,`team3_medallion`.`f`.`source_system` AS `source_system`,`team3_medallion`.`f`.`matched_checkin_id` AS `matched_checkin_id`,`team3_medallion`.`f`.`matched_session_id` AS `matched_session_id`,`team3_medallion`.`f`.`matched_hospital_department_id` AS `matched_hospital_department_id`,`team3_medallion`.`f`.`matched_hospital_id` AS `matched_hospital_id`,`team3_medallion`.`f`.`matched_department_code` AS `matched_department_code`,`team3_medallion`.`f`.`hospital_name` AS `hospital_name`,`team3_medallion`.`f`.`department_name` AS `department_name`,`team3_medallion`.`f`.`hospital_group` AS `hospital_group`,`team3_medallion`.`f`.`department_group` AS `department_group`,`team3_medallion`.`f`.`treatment_month` AS `treatment_month`,`team3_medallion`.`f`.`context_status` AS `context_status`,`team3_medallion`.`f`.`transaction_rows` AS `transaction_rows`,`team3_medallion`.`f`.`payment_rows` AS `payment_rows`,`team3_medallion`.`f`.`refund_rows` AS `refund_rows`,`team3_medallion`.`f`.`paid_amount` AS `paid_amount`,`team3_medallion`.`f`.`refunded_amount` AS `refunded_amount`,`team3_medallion`.`f`.`recorded_net_amount` AS `recorded_net_amount`,`team3_medallion`.`f`.`transaction_gap` AS `transaction_gap`,`team3_medallion`.`f`.`service_amount` AS `service_amount`,`team3_medallion`.`f`.`service_gap` AS `service_gap`,`team3_medallion`.`f`.`service_rows` AS `service_rows`,`team3_medallion`.`f`.`invalid_transaction_rows` AS `invalid_transaction_rows`,`team3_medallion`.`f`.`missing_transaction_time_rows` AS `missing_transaction_time_rows`,`team3_medallion`.`f`.`invalid_service_rows` AS `invalid_service_rows`,`team3_medallion`.`f`.`quarantine_payment_rows` AS `quarantine_payment_rows`,`team3_medallion`.`f`.`quarantine_service_rows` AS `quarantine_service_rows`,`team3_medallion`.`f`.`first_payment_at` AS `first_payment_at`,`team3_medallion`.`f`.`last_payment_at` AS `last_payment_at`,`team3_medallion`.`f`.`first_transaction_at` AS `first_transaction_at`,`team3_medallion`.`f`.`last_transaction_at` AS `last_transaction_at`,`team3_medallion`.`f`.`first_payment_minutes_from_end` AS `first_payment_minutes_from_end`,`team3_medallion`.`f`.`method_bundle` AS `method_bundle`,`team3_medallion`.`f`.`evidence_status` AS `evidence_status`,(case when ((`team3_medallion`.`f`.`started_at` is not null) and (`team3_medallion`.`f`.`ended_at` is not null) and (`team3_medallion`.`f`.`ended_at` >= `team3_medallion`.`f`.`started_at`) and (`team3_medallion`.`f`.`ended_at` < '2026-01-01')) then 1 else 0 end) AS `completed_in_observation`,coalesce(`t`.`payments_at_or_after_end`,0) AS `payments_at_or_after_end`,coalesce(`t`.`payments_before_end`,0) AS `payments_before_end`,coalesce(`t`.`different_end_date_transactions`,0) AS `different_end_date_transactions`,(case when ((`team3_medallion`.`f`.`started_at` is null) or (`team3_medallion`.`f`.`ended_at` is null) or (`team3_medallion`.`f`.`ended_at` < `team3_medallion`.`f`.`started_at`)) then 'HOLD_COMPLETION_UNKNOWN' when (`team3_medallion`.`f`.`ended_at` >= '2026-01-01') then 'OUTSIDE_OBSERVATION' when ((`team3_medallion`.`f`.`net_charge` is null) or (`team3_medallion`.`f`.`gross_charge` is null) or (`team3_medallion`.`f`.`authorized_refund` is null) or (`team3_medallion`.`f`.`gross_charge` < 0) or (`team3_medallion`.`f`.`authorized_refund` < 0) or (`team3_medallion`.`f`.`authorized_refund` > `team3_medallion`.`f`.`gross_charge`) or (`team3_medallion`.`f`.`net_charge` <> (`team3_medallion`.`f`.`gross_charge` - `team3_medallion`.`f`.`authorized_refund`))) then 'HOLD_CHARGE_INVALID' when ((`team3_medallion`.`f`.`invalid_transaction_rows` > 0) or (`team3_medallion`.`f`.`missing_transaction_time_rows` > 0)) then 'HOLD_TRANSACTION_INVALID' when ((`team3_medallion`.`f`.`quarantine_payment_rows` > 0) or (`team3_medallion`.`f`.`quarantine_service_rows` > 0)) then 'HOLD_LINKED_QUARANTINE' when ((coalesce(`r`.`invalid_refund_links`,0) > 0) or (coalesce(`x`.`excessive_refund_originals`,0) > 0)) then 'HOLD_REFUND_LINK_OR_TOTAL' when ((`team3_medallion`.`f`.`invalid_service_rows` > 0) or (`team3_medallion`.`f`.`service_rows` = 0)) then 'HOLD_SERVICE_EVIDENCE' when (`team3_medallion`.`f`.`last_transaction_at` >= '2026-01-01') then 'HOLD_AFTER_OBSERVATION' else 'ASSESSABLE_CURRENT_LINKED_RECORDS' end) AS `judgement_status` from (((`team3_medallion`.`baek_gold_encounter_finance` `f` left join `bad_refunds` `r` on((`r`.`encounter_id` = `team3_medallion`.`f`.`encounter_id`))) left join `excessive` `x` on((`x`.`encounter_id` = `team3_medallion`.`f`.`encounter_id`))) left join `timing` `t` on((`t`.`encounter_id` = `team3_medallion`.`f`.`encounter_id`)));

SET UNIQUE_CHECKS = 1;
SET FOREIGN_KEY_CHECKS = 1;

-- ---------------------------------------------------------------- 4. 건수 확인 (expected 와 actual 이 같아야 함)
SELECT 'team3_medallion' AS schema_name, 'encounter_services' AS table_name, 1490589 AS expected, COUNT(*) AS actual FROM `team3_medallion`.`encounter_services`
UNION ALL SELECT 'team3_medallion' AS schema_name, 'appointment_events' AS table_name, 1365801 AS expected, COUNT(*) AS actual FROM `team3_medallion`.`appointment_events`
UNION ALL SELECT 'team3_medallion' AS schema_name, 'payments' AS table_name, 732464 AS expected, COUNT(*) AS actual FROM `team3_medallion`.`payments`
UNION ALL SELECT 'team3_medallion' AS schema_name, 'checkins' AS table_name, 843340 AS expected, COUNT(*) AS actual FROM `team3_medallion`.`checkins`
UNION ALL SELECT 'team3_medallion' AS schema_name, 'appointments' AS table_name, 714682 AS expected, COUNT(*) AS actual FROM `team3_medallion`.`appointments`
UNION ALL SELECT 'team3_medallion' AS schema_name, 'appointment_slots' AS table_name, 925770 AS expected, COUNT(*) AS actual FROM `team3_medallion`.`appointment_slots`
UNION ALL SELECT 'team3_medallion' AS schema_name, 'encounters' AS table_name, 496863 AS expected, COUNT(*) AS actual FROM `team3_medallion`.`encounters`
UNION ALL SELECT 'team3_medallion' AS schema_name, 'clinic_sessions' AS table_name, 241517 AS expected, COUNT(*) AS actual FROM `team3_medallion`.`clinic_sessions`
UNION ALL SELECT 'team3_medallion' AS schema_name, 'patients' AS table_name, 291001 AS expected, COUNT(*) AS actual FROM `team3_medallion`.`patients`
UNION ALL SELECT 'team3_medallion' AS schema_name, 'doctor_assignments' AS table_name, 12754 AS expected, COUNT(*) AS actual FROM `team3_medallion`.`doctor_assignments`
UNION ALL SELECT 'team3_medallion' AS schema_name, 'doctors' AS table_name, 4748 AS expected, COUNT(*) AS actual FROM `team3_medallion`.`doctors`
UNION ALL SELECT 'team3_medallion' AS schema_name, 'hospital_departments' AS table_name, 1870 AS expected, COUNT(*) AS actual FROM `team3_medallion`.`hospital_departments`
UNION ALL SELECT 'team3_medallion' AS schema_name, 'hospitals' AS table_name, 485 AS expected, COUNT(*) AS actual FROM `team3_medallion`.`hospitals`
UNION ALL SELECT 'team3_medallion' AS schema_name, 'service_catalog' AS table_name, 180 AS expected, COUNT(*) AS actual FROM `team3_medallion`.`service_catalog`
UNION ALL SELECT 'team3_medallion' AS schema_name, 'departments' AS table_name, 12 AS expected, COUNT(*) AS actual FROM `team3_medallion`.`departments`
UNION ALL SELECT 'team3_medallion' AS schema_name, 'code_dictionary' AS table_name, 36 AS expected, COUNT(*) AS actual FROM `team3_medallion`.`code_dictionary`
UNION ALL SELECT 'team3_medallion' AS schema_name, 'legacy_code_mappings' AS table_name, 72 AS expected, COUNT(*) AS actual FROM `team3_medallion`.`legacy_code_mappings`
UNION ALL SELECT 'team3_medallion_dq' AS schema_name, 'checkins_quarantine' AS table_name, 225121 AS expected, COUNT(*) AS actual FROM `team3_medallion_dq`.`checkins_quarantine`
UNION ALL SELECT 'team3_medallion_dq' AS schema_name, 'reclean_finance_before' AS table_name, 538154 AS expected, COUNT(*) AS actual FROM `team3_medallion_dq`.`reclean_finance_before`
UNION ALL SELECT 'team3_medallion_dq' AS schema_name, 'appointment_slots_quarantine' AS table_name, 211855 AS expected, COUNT(*) AS actual FROM `team3_medallion_dq`.`appointment_slots_quarantine`
UNION ALL SELECT 'team3_medallion_dq' AS schema_name, 'encounter_services' AS table_name, 555496 AS expected, COUNT(*) AS actual FROM `team3_medallion_dq`.`encounter_services`
UNION ALL SELECT 'team3_medallion_dq' AS schema_name, 'reclean_exceptions' AS table_name, 308664 AS expected, COUNT(*) AS actual FROM `team3_medallion_dq`.`reclean_exceptions`
UNION ALL SELECT 'team3_medallion_dq' AS schema_name, 'reclean_repairs' AS table_name, 33016 AS expected, COUNT(*) AS actual FROM `team3_medallion_dq`.`reclean_repairs`
UNION ALL SELECT 'team3_medallion_dq' AS schema_name, 'encounters' AS table_name, 240050 AS expected, COUNT(*) AS actual FROM `team3_medallion_dq`.`encounters`
UNION ALL SELECT 'team3_medallion_dq' AS schema_name, 'payments_quarantine' AS table_name, 88006 AS expected, COUNT(*) AS actual FROM `team3_medallion_dq`.`payments_quarantine`
UNION ALL SELECT 'team3_medallion_dq' AS schema_name, 'checkins_dual_pairs' AS table_name, 154712 AS expected, COUNT(*) AS actual FROM `team3_medallion_dq`.`checkins_dual_pairs`
UNION ALL SELECT 'team3_medallion_dq' AS schema_name, 'clinic_sessions_quarantine' AS table_name, 42198 AS expected, COUNT(*) AS actual FROM `team3_medallion_dq`.`clinic_sessions_quarantine`
UNION ALL SELECT 'team3_medallion_dq' AS schema_name, 'reclean_excluded_mirrors' AS table_name, 8381 AS expected, COUNT(*) AS actual FROM `team3_medallion_dq`.`reclean_excluded_mirrors`
UNION ALL SELECT 'team3_medallion_dq' AS schema_name, 'checkins_excluded' AS table_name, 6001 AS expected, COUNT(*) AS actual FROM `team3_medallion_dq`.`checkins_excluded`
UNION ALL SELECT 'team3_medallion_dq' AS schema_name, 'payments_excluded' AS table_name, 7501 AS expected, COUNT(*) AS actual FROM `team3_medallion_dq`.`payments_excluded`
UNION ALL SELECT 'team3_medallion_dq' AS schema_name, 'doctor_assignments_quarantine' AS table_name, 1356 AS expected, COUNT(*) AS actual FROM `team3_medallion_dq`.`doctor_assignments_quarantine`
UNION ALL SELECT 'team3_medallion_dq' AS schema_name, 'doctors_quarantine' AS table_name, 252 AS expected, COUNT(*) AS actual FROM `team3_medallion_dq`.`doctors_quarantine`
UNION ALL SELECT 'team3_medallion_dq' AS schema_name, 'departments_excluded' AS table_name, 0 AS expected, COUNT(*) AS actual FROM `team3_medallion_dq`.`departments_excluded`
UNION ALL SELECT 'team3_medallion_dq' AS schema_name, 'departments_quarantine' AS table_name, 0 AS expected, COUNT(*) AS actual FROM `team3_medallion_dq`.`departments_quarantine`
UNION ALL SELECT 'team3_medallion_dq' AS schema_name, 'doctor_assignments_excluded' AS table_name, 0 AS expected, COUNT(*) AS actual FROM `team3_medallion_dq`.`doctor_assignments_excluded`
UNION ALL SELECT 'team3_medallion_dq' AS schema_name, 'doctors_excluded' AS table_name, 0 AS expected, COUNT(*) AS actual FROM `team3_medallion_dq`.`doctors_excluded`
UNION ALL SELECT 'team3_medallion_dq' AS schema_name, 'hospital_departments_excluded' AS table_name, 0 AS expected, COUNT(*) AS actual FROM `team3_medallion_dq`.`hospital_departments_excluded`
UNION ALL SELECT 'team3_medallion_dq' AS schema_name, 'hospital_departments_quarantine' AS table_name, 71 AS expected, COUNT(*) AS actual FROM `team3_medallion_dq`.`hospital_departments_quarantine`
UNION ALL SELECT 'team3_medallion_dq' AS schema_name, 'clinic_sessions_excluded' AS table_name, 0 AS expected, COUNT(*) AS actual FROM `team3_medallion_dq`.`clinic_sessions_excluded`
UNION ALL SELECT 'team3_medallion_dq' AS schema_name, 'appointment_slots_excluded' AS table_name, 0 AS expected, COUNT(*) AS actual FROM `team3_medallion_dq`.`appointment_slots_excluded`
UNION ALL SELECT 'team3_medallion_dq' AS schema_name, 'cross_recovery_log_20261015' AS table_name, 0 AS expected, COUNT(*) AS actual FROM `team3_medallion_dq`.`cross_recovery_log_20261015`;
