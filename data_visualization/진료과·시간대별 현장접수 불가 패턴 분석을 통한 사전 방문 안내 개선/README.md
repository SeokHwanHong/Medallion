# 현장접수 시각화·보고서 코드

- `charts.py`: 도표와 PDF의 공통 글꼴·색상·표·그래프 함수.
- `visualize_walk_in.py`: 진료과별 비교, 시간대 히트맵, 상위 4개 월별 반복성 도표를 PDF·PNG로 생성.
- `generate_report.py`: 주장·근거·개선안을 담은 4쪽 보고서를 `report`에 생성. 같은 이름은 버전 번호를 붙여 보존.
- `requirements.txt`: 이 주제의 분석·시각화 실행 패키지.

프로젝트 루트에서 실행합니다. 먼저 같은 주제의 `analyze_walk_in.py`로 분석 JSON을 만드세요.

```powershell
python -m pip install -r "data_visualization/진료과·시간대별 현장접수 불가 패턴 분석을 통한 사전 방문 안내 개선/requirements.txt"
python "data_visualization/진료과·시간대별 현장접수 불가 패턴 분석을 통한 사전 방문 안내 개선/visualize_walk_in.py"
python "data_visualization/진료과·시간대별 현장접수 불가 패턴 분석을 통한 사전 방문 안내 개선/generate_report.py"
```

두 명령은 `--analysis-json`, `--output-dir`로 경로를 지정할 수 있습니다. 도표는 기본적으로 이 코드 폴더에 저장하며 기존 도표는 덮어쓰지 않습니다. 맑은 고딕이 설치된 Windows를 기준으로 작성했습니다.

보고서 본문 수치는 검토된 2023~2025년 CSV 스냅샷 전용입니다. 입력 해시가 다르면 생성을 중단하므로 새 데이터에는 본문과 결론을 다시 검토해야 합니다. 작성일은 원래 분석 보고서 작성일(2026-10-16)입니다.

DB 접속·예측·시뮬레이션·가상 데이터 생성은 하지 않습니다. 임시 검증 파일이나 Notion 업로드 자격 정보는 포함하지 않았습니다.
