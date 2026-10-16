# -*- coding: utf-8 -*-
"""
[황유민] MySQL(team3_medallion, team3_medallion_dq) 조회 결과를 GitHub 에 올릴 수 있는 CSV + 생성·적재 SQL 로 바꾼다.

입력: mysql 클라이언트 배치 모드(-B --quick) 출력 파일 1개
      (조회 SQL: export_queries.sql. 테이블마다 '##TABLE##' 표시 → SHOW CREATE TABLE → SELECT * 순서. 조회 전용 세션)
출력: data/<스키마>/<테이블>.csv  (90MB 를 넘으면 <테이블>_part01.csv, _part02.csv ... 로 나눔, 파일마다 헤더 포함)
      build_db.sql                (DB 생성 → 테이블 생성 → CSV 적재 → 뷰 생성 → 건수 확인)
      table_manifest.csv          (테이블별 행 수, 파일 수, 용량)

CSV 규칙: UTF-8(BOM 없음), 쉼표 구분, 줄바꿈 LF, 값은 모두 큰따옴표로 감쌈(안의 " 는 ""), NULL 은 따옴표 없는 NULL.
          (MySQL LOAD DATA 의 'OPTIONALLY ENCLOSED BY ... ESCAPED BY ""' 규칙과 같아서 NULL 과 문자열 'NULL' 이 구분된다)
실행: python -I export_to_csv.py <배치 출력 파일> <GIT DB 폴더> [원본 DDL 파일 ...]  (원본 DDL 은 깨진 한글 COMMENT 복구용)
"""
import csv
import os
import re
import sys

RAW, ROOT = sys.argv[1], sys.argv[2]
LIMIT = 90 * 1024 * 1024          # GitHub 파일당 100MB 제한보다 여유 있게
DATA = os.path.join(ROOT, "data")
UNESC = re.compile(r"\\(.)")
UNESC_MAP = {"n": "\n", "t": "\t", "0": "\0", "\\": "\\", "b": "\b", "r": "\r", "Z": "\x1a"}


def unescape(v):
    """배치 모드 출력값 → 원래 값. 'NULL' 은 None."""
    if v == "NULL":
        return None
    return UNESC.sub(lambda m: UNESC_MAP.get(m.group(1), m.group(1)), v)


def csv_line(vals):
    out = []
    for v in vals:
        if v is None:
            out.append("NULL")
        else:
            out.append('"' + v.replace('"', '""') + '"')
    return ",".join(out) + "\n"


class Writer:
    """테이블 하나를 90MB 단위 파일로 나눠 쓴다."""

    def __init__(self, schema, table, header):
        self.dir = os.path.join(DATA, schema)
        os.makedirs(self.dir, exist_ok=True)
        self.schema, self.table = schema, table
        self.header = csv_line(header).encode("utf-8")
        self.part, self.size, self.rows, self.fh, self.files = 0, 0, 0, None, []
        self._open()

    def _open(self):
        if self.fh:
            self.fh.close()
        self.part += 1
        path = os.path.join(self.dir, f"{self.table}_part{self.part:02d}.csv")
        self.files.append(path)
        self.fh = open(path, "wb")
        self.fh.write(self.header)
        self.size = len(self.header)

    def write(self, vals):
        b = csv_line(vals).encode("utf-8")
        if self.size + len(b) > LIMIT and self.size > len(self.header):
            self._open()
        self.fh.write(b)
        self.size += len(b)
        self.rows += 1

    def close(self):
        self.fh.close()
        if len(self.files) == 1:      # 한 파일이면 _part01 을 떼어 낸다
            single = os.path.join(self.dir, f"{self.table}.csv")
            os.replace(self.files[0], single)
            self.files = [single]
        return self.files


def lines(path):
    with open(path, "r", encoding="utf-8", newline="\n") as fh:
        for ln in fh:
            yield ln.rstrip("\n").rstrip("\r")


# ------------------------------------------------------------------ 배치 출력 파싱
objects = []          # (schema, table, kind, ddl, files, rows, columns)
it = lines(RAW)
buf = []


def nxt():
    if buf:
        return buf.pop()
    return next(it, None)


def is_marker(line):
    if line != "m\tt":
        return False
    peek = nxt()
    buf.append(peek)
    return peek is not None and peek.startswith("##TABLE##\t")


line = nxt()
while line is not None:
    if not is_marker(line):
        line = nxt()
        continue
    full = nxt().split("\t", 1)[1]
    schema, table = full.split(".", 1)
    ddl_head = nxt().split("\t")
    ddl_row = [unescape(v) for v in nxt().split("\t")]
    kind = "VIEW" if ddl_head[0] == "View" else "TABLE"
    ddl = ddl_row[1]
    writer, columns = None, None
    line = nxt()
    if kind == "TABLE":
        if line is not None and not is_marker(line):        # 데이터가 있는 테이블: 첫 줄은 컬럼 이름
            columns = line.split("\t")
            writer = Writer(schema, table, columns)
            line = nxt()
            while line is not None and not is_marker(line):
                writer.write([unescape(v) for v in line.split("\t")])
                line = nxt()
        else:                                                # 0행 테이블: DDL 에서 컬럼 이름만 뽑아 헤더만 있는 CSV
            columns = re.findall(r"^\s+`([^`]+)`\s", ddl, flags=re.M)
            writer = Writer(schema, table, columns)
    files = writer.close() if writer else []
    rows = writer.rows if writer else 0
    objects.append((schema, table, kind, ddl, files, rows, columns))
    print(f"{schema}.{table:40s} {kind:5s} rows={rows:>10,} files={len(files)}", flush=True)

# ------------------------------------------------------------------ manifest
with open(os.path.join(ROOT, "table_manifest.csv"), "w", encoding="utf-8", newline="") as fh:
    w = csv.writer(fh)
    w.writerow(["schema", "table", "type", "rows", "files", "size_mb"])
    for s, t, k, _, files, rows, _ in objects:
        w.writerow([s, t, k, rows, len(files), round(sum(os.path.getsize(f) for f in files) / 1048576, 1)])

# ------------------------------------------------------------------ build_db.sql
def rel(p):
    return os.path.relpath(p, ROOT).replace("\\", "/")


def clean_view(ddl):
    ddl = re.sub(r"DEFINER=`[^`]+`@`[^`]+`\s*", "", ddl)
    ddl = re.sub(r"SQL SECURITY DEFINER\s*", "", ddl)
    return ddl.replace("CREATE ALGORITHM=UNDEFINED", "CREATE OR REPLACE ALGORITHM=UNDEFINED", 1)


# ---- 깨진 한글 COMMENT 복구: 원래 DB 의 COMMENT 는 cp949 콘솔에서 실행돼 글자가 깨져 있다(데이터 값은 정상).
#      ① 원본 DDL 파일(정상 한글)의 같은 테이블·컬럼 설명 → ② 깨진 글자 되돌리기(UTF-8 을 cp949 로 읽은 것) → ③ 안 되면 COMMENT 삭제
SRC_COMMENTS = {}
for src in sys.argv[3:]:
    cur = None
    for ln in open(src, encoding="utf-8"):
        m = re.match(r"\s*CREATE TABLE (?:IF NOT EXISTS )?`?(\w+)`?", ln, flags=re.I)
        if m:
            cur = m.group(1)
            SRC_COMMENTS.setdefault(cur, {})
            continue
        if cur is None:
            continue
        m = re.match(r"\s*`?(\w+)`?\s+\w+.*?COMMENT\s+'([^']*)'", ln)
        if m and not ln.strip().upper().startswith(("PRIMARY", "UNIQUE", "KEY", "CONSTRAINT", "INDEX")):
            SRC_COMMENTS[cur][m.group(1)] = m.group(2)
        m = re.search(r"\)\s.*COMMENT\s*=\s*'([^']*)'", ln)
        if m:
            SRC_COMMENTS[cur]["__table__"] = m.group(1)
fix_stats = {"source": 0, "reversed": 0, "dropped": 0}


def reverse_mojibake(s):
    try:
        r = s.encode("cp949").decode("utf-8")
        return r if "?" not in s else None
    except (UnicodeEncodeError, UnicodeDecodeError):
        return None


def fix_comments(table, ddl):
    src = SRC_COMMENTS.get(table, {})
    out = []
    for ln in ddl.split("\n"):
        m = re.match(r"(\s*`(\w+)`.*?)( COMMENT '((?:[^']|'')*)')(.*)$", ln)
        mt = re.match(r"(\).*?)( COMMENT='((?:[^']|'')*)')(.*)$", ln)
        if m:
            col, text = m.group(2), m.group(4)
            if col in src:
                new, k = src[col], "source"
            else:
                new = reverse_mojibake(text)
                k = "reversed" if new else "dropped"
            fix_stats[k] += 1
            ln = m.group(1) + (f" COMMENT '{new}'" if new else "") + m.group(5)
        elif mt:
            text = mt.group(3)
            if "__table__" in src:
                new, k = src["__table__"], "source"
            else:
                new = reverse_mojibake(text)
                k = "reversed" if new else "dropped"
            fix_stats[k] += 1
            ln = mt.group(1) + (f" COMMENT='{new}'" if new else "") + mt.group(4)
        out.append(ln)
    return "\n".join(out)


objects = [(s, t, k, fix_comments(t, ddl) if k == "TABLE" else ddl, f, r, c) for s, t, k, ddl, f, r, c in objects]
print("comment fix", fix_stats)

tables = [o for o in objects if o[2] == "TABLE"]
views = [o for o in objects if o[2] == "VIEW"]
# 뷰는 다른 뷰를 참조하므로, 참조되는 뷰가 먼저 만들어지도록 순서를 정한다(위상 정렬)
names = {o[1] for o in views}
deps = {o[1]: {n for n in names if n != o[1] and re.search(rf"`{n}`", o[3])} for o in views}
ordered, done = [], set()
while len(ordered) < len(views):
    ready = [o for o in views if o[1] not in done and deps[o[1]] <= done]
    if not ready:                      # 순환 참조가 있으면 남은 것을 그대로 붙인다
        ready = [o for o in views if o[1] not in done]
    for o in sorted(ready, key=lambda x: x[1]):
        ordered.append(o)
        done.add(o[1])
views = ordered
L = []
L.append("-- ============================================================================")
L.append("-- team3 MySQL DB 생성·적재 규칙 (build_db.sql)")
L.append("-- 대상 스키마: team3_medallion (정제 데이터, Silver) / team3_medallion_dq (격리·제외·재정제 기록)")
L.append("-- 실행 위치: 이 파일이 있는 폴더 (CSV 경로가 data/... 상대 경로)")
L.append("--   mysql --local-infile=1 -u <계정> -p < build_db.sql")
L.append("-- 전제: 빈 MySQL 8.x 서버. 서버 설정 local_infile=ON 필요 (SET GLOBAL local_infile = 1;)")
L.append("-- CSV 규칙: UTF-8, 쉼표, LF, 값은 큰따옴표로 감쌈, NULL 은 따옴표 없는 NULL")
L.append("-- 테이블 구조는 원래 DB 의 SHOW CREATE TABLE 결과를 그대로 사용한다.")
L.append("-- 제외: 재정제 실행 로그 3개(reclean_quarantine, reclean_issues, reclean_parent_keys, 합계 약 3.8GB)는 용량 때문에 포함하지 않음")
L.append("-- ============================================================================")
L.append("SET NAMES utf8mb4;")
L.append("SET FOREIGN_KEY_CHECKS = 0;")
L.append("SET UNIQUE_CHECKS = 0;")
for s in ("team3_medallion", "team3_medallion_dq"):
    L.append(f"CREATE DATABASE IF NOT EXISTS `{s}` CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;")
L.append("")
L.append("-- ---------------------------------------------------------------- 1. 테이블 생성")
for s, t, _, ddl, _, _, _ in tables:
    L.append(f"USE `{s}`;")
    L.append(ddl.replace("CREATE TABLE ", "CREATE TABLE IF NOT EXISTS ", 1) + ";")
    L.append("")
L.append("-- ---------------------------------------------------------------- 2. CSV 적재")
for s, t, _, _, files, _, _ in tables:
    for f in files:
        L.append(f"LOAD DATA LOCAL INFILE '{rel(f)}' INTO TABLE `{s}`.`{t}` CHARACTER SET utf8mb4")
        L.append("  FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '\"' ESCAPED BY '' LINES TERMINATED BY '\\n' IGNORE 1 LINES;")
L.append("")
L.append("-- ---------------------------------------------------------------- 3. 뷰 생성 (데이터 없음, 다른 테이블에서 계산)")
for s, t, _, ddl, _, _, _ in views:
    L.append(f"USE `{s}`;")
    L.append(clean_view(ddl) + ";")
L.append("")
L.append("SET UNIQUE_CHECKS = 1;")
L.append("SET FOREIGN_KEY_CHECKS = 1;")
L.append("")
L.append("-- ---------------------------------------------------------------- 4. 건수 확인 (expected 와 actual 이 같아야 함)")
parts = [f"SELECT '{s}' AS schema_name, '{t}' AS table_name, {rows} AS expected, COUNT(*) AS actual FROM `{s}`.`{t}`"
         for s, t, _, _, _, rows, _ in tables]
L.append("\nUNION ALL ".join(parts) + ";")
open(os.path.join(ROOT, "build_db.sql"), "w", encoding="utf-8", newline="\n").write("\n".join(L) + "\n")
print("tables", len(tables), "views", len(views))
