# 수납·재정 대사 검증 및 창구 업무 복잡도 최적화 — 분석 코드 (`data_analysis`)

본 디렉터리는 **소주제: 수납·재정 대사 정합성 검증 및 창구 업무 복잡도 최적화**의 MySQL 8.4 메달리온(Silver 7종 · Gold 3종) 뷰 정의 SQL, 오프라인 집계 SQL(S01~S08), 추출 결과 CSV 및 Python 분석/검증 스크립트를 포함합니다.

## 파일 구성
- `01_build_silver_views.sql`: MySQL 8.4 `baek_silver_*` 정합성 검증 뷰 7종 생성 SQL (`CREATE OR REPLACE VIEW`, 원본 테이블 무수정)
- `02_build_gold_views.sql`: MySQL 8.4 `baek_gold_*` 주제 마트 뷰 3종 생성 SQL (`baek_gold_encounter_collection_mart`, `baek_gold_refund_trace`, `baek_gold_collection_topic`)
- `03_collection_topic_queries.sql`: Gold 마트 기반 핵심 대사 및 창구 복잡도 검증 SQL
- `sql/S01_final_finance.sql` ~ `S08_final_hospital.sql`: 최종 DB 재정 대사(496,863건), 시나리오 작업량(1,749건), 과거 기준 대사 근거 분류, 시간대별(08~14시) 집중도 조회 SQL
- `results/S01_final_finance.csv` ~ `S08_final_hospital.csv`: 위 SQL의 실행 결과 스냅샷 CSV
- `analyze_collection_workload.py`: 추출된 CSV(`S01`~`S08`)를 바탕으로 수납 대사 정합성, 시간대별 복수거래 집중도, 시나리오별 창구 인일(Man-Day) 민감도를 계산하는 분석 코드
- `verify_reconciliation_12tests.py`: 12대 교차검증(Cross-Validation) 테스트 실행 코드
- `소주제_수납대사검증_및_창구업무복잡도최적화_골드인사이트_및_논리구조.md`: 골드 인사이트, Man-Day 산출 수식 및 3단 논리 방어 Q&A 문서

## 실행 방법
```powershell
python "data_analysis/소주제_수납대사검증_및_창구업무복잡도최적화/analyze_collection_workload.py"
```
시각화 차트 및 발표자료 생성 코드는 `data_visualization/소주제_수납대사검증_및_창구업무복잡도최적화/` 폴더를 참고하세요.

