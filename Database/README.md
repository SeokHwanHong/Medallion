# GIT DB: team3 MySQL DB 를 CSV 로 옮긴 폴더

MySQL DB(`team3_medallion`, `team3_medallion_dq`)의 내용을 GitHub 에 올릴 수 있도록 CSV 와 생성·적재 SQL 로 바꿔 둔 폴더입니다.
이 폴더만 있으면 빈 MySQL 서버에 같은 DB 를 다시 만들 수 있습니다.

- 추출: 2026-10-16, 조회 전용 세션(`SET SESSION TRANSACTION READ ONLY`)에서 `SHOW CREATE TABLE`, `SELECT *` 만 실행
- 정리: 황유민

## 구성

| 경로 | 내용 |
|---|---|
| `build_db.sql` | **DB 생성·적재 규칙 파일.** 스키마 생성 → 테이블 41개 생성 → CSV 44개 적재 → 뷰 10개 생성 → 테이블별 건수 확인 |
| `data/team3_medallion/` | 정제 데이터(Silver) 17개 테이블, 7,122,184행, 약 704MB |
| `data/team3_medallion_dq/` | 격리·제외·재정제 기록 24개 테이블, 2,420,834행, 약 332MB |
| `table_manifest.csv` | 테이블별 행 수, 파일 수, 용량 |
| `scripts/export_queries.sql` | DB 에서 구조와 데이터를 뽑은 조회 SQL (조회 전용) |
| `scripts/export_to_csv.py` | 조회 결과 → CSV + `build_db.sql` 변환 코드 |

- 100MB 가 넘는 테이블은 `_part01.csv`, `_part02.csv` 로 나눴습니다(GitHub 파일당 100MB 제한). 모든 파일이 90MB 이하입니다.
  나뉜 테이블: `encounter_services`, `appointment_events`, `checkins` (각 2개 파일)
- `team3_medallion` 의 `baek_*` 10개는 다른 테이블에서 계산되는 **뷰**라 데이터 파일이 없고, `build_db.sql` 에 정의만 들어 있습니다.

## 포함하지 않은 것

재정제 실행 로그 3개는 용량이 커서(합계 약 3.8GB) 넣지 않았습니다. 정제를 다시 돌리면 생기는 기록입니다.

| 테이블 | 행 수 | 용량 |
|---|---|---|
| `team3_medallion_dq.reclean_quarantine` | 약 260만 | 약 2.5GB |
| `team3_medallion_dq.reclean_issues` | 약 250만 | 약 0.7GB |
| `team3_medallion_dq.reclean_parent_keys` | 약 300만 | 약 0.6GB |

## DB 다시 만들기

1. MySQL 서버에서 로컬 파일 적재를 켭니다: `SET GLOBAL local_infile = 1;`
2. 이 폴더에서 실행합니다(CSV 경로가 `data/...` 상대 경로):

```
mysql --local-infile=1 -u <계정> -p < build_db.sql
```

3. 마지막에 나오는 표에서 `expected` 와 `actual` 이 모두 같은지 확인합니다.

빈 서버에서 실행하는 것을 전제로 합니다. 같은 이름의 DB 에 데이터가 이미 있으면 같은 행이 두 번 들어가거나 키 중복 오류가 납니다.

## CSV 규칙

- UTF-8(BOM 없음), 쉼표 구분, 줄바꿈 LF, 첫 줄은 컬럼 이름
- 값은 모두 큰따옴표로 감싸고, 값 안의 `"` 는 `""` 로 씁니다
- **NULL 은 따옴표 없는 `NULL`** 입니다. 따옴표로 감싼 `"NULL"` 은 문자열입니다
- 파이썬으로 읽을 때: pandas 는 기본 설정으로 `NULL` 을 결측값으로 읽고, Polars 는 `pl.read_csv(path, null_values="NULL")` 처럼 지정합니다
- 나뉜 테이블은 `_part*.csv` 를 모두 이어 붙여 읽습니다

## 참고

- 원래 DB 의 테이블·컬럼 설명(COMMENT) 한글이 DB 안에서 깨져 있어(데이터 값의 한글은 정상), `build_db.sql` 에는 원본 DDL 파일의 정상 한글 설명 165개로 바꿔 넣었습니다.
- `build_db.sql` 은 실제 서버에서 실행해 보지 않았습니다. 처음 실행할 때 마지막 건수 확인 결과를 꼭 봐 주세요.
- 비밀번호·접속 정보는 이 폴더에 없습니다.
