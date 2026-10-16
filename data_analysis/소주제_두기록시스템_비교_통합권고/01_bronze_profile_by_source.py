# -*- coding: utf-8 -*-
"""
[황유민] Bronze(수신 원본 CSV) 품질 결함을 원천 시스템(LEGACY_A / LEGACY_B)별로 집계한다.
- 입력: data/<테이블>/*.csv (읽기 전용, 엑셀 잠금 파일 ~$ 제외)
- 출력: out/bronze_defects_by_source.csv (테이블 x 원천 x 컬럼 x 결함 유형 건수)
        out/bronze_rows_by_source.csv    (테이블 x 원천: 행 수, 결함 행 수, 결함률)
- 결함 판정은 정제 규칙(B14, B15)과 같은 기준: 공백, ID 하이픈, 더미 ID, 형식 오류 ID, 결측, 슬래시 날짜,
  존재하지 않는 날짜, 코드 별칭(복구 가능), 미등록 코드, 음수, 숫자 아님, 길이 초과, 완전 중복 행.
실행: python -I 01_bronze_profile_by_source.py <data 폴더> <출력 폴더>
"""
import glob
import os
import sys

import polars as pl

DATA, OUT = sys.argv[1], sys.argv[2]
os.makedirs(OUT, exist_ok=True)


def read(t):
    fs = [f for f in sorted(glob.glob(os.path.join(DATA, t, "*.csv"))) if not os.path.basename(f).startswith("~$")]
    return pl.concat([pl.read_csv(f, infer_schema=False) for f in fs])


cd = read("code_dictionary")
lm = read("legacy_code_mappings")
STD = {}
for dom, code in zip(cd["domain"], cd["standard_code"]):
    STD.setdefault(dom, set()).add(code)
ALIAS = {}
for dom, raw in zip(lm["domain"], lm["raw_code"]):
    ALIAS.setdefault(dom, set()).add(raw)

NUMERIC = {"capacity", "quantity", "unit_price", "line_amount", "gross_charge", "authorized_refund", "net_charge",
           "amount", "allocation_pct", "line_no", "event_seq", "last_event_seq"}
DATES = {"valid_from", "valid_to", "slot_start", "slot_end", "session_start", "session_end", "started_at", "ended_at",
         "booked_at", "scheduled_at", "event_at", "arrival_at", "checked_in_at", "transacted_at", "registered_at",
         "birth_date", "hire_date", "opened_date"}
NULLABLE = {("checkins", "appointment_id"), ("payments", "original_payment_id")}
NAMES = {"hospital_name": 100, "doctor_name": 100, "service_name": 100, "department_name": 100}
SKIP_COLS = {"source_system", "label", "dictionary_version", "mapping_version", "region_code", "dictionary_id", "mapping_id",
             "raw_code", "standard_code", "domain"}
TABLES = [t for t in sorted(os.listdir(DATA)) if t not in ("code_dictionary", "legacy_code_mappings")]


def checks(t, col):
    """(결함 유형, 조건식) 목록. 조건이 참이면 그 행의 해당 컬럼에 결함."""
    raw = pl.col(col)
    s = raw.str.strip_chars()
    out = []
    blank = raw.is_null() | (s == "")
    if (t, col) not in NULLABLE:
        out.append(("결측(필수값 빈칸)", blank))
    out.append(("앞뒤 공백", raw.is_not_null() & (raw != s)))
    if col.endswith("_id") or col in ("department_code", "service_code"):
        v = s.str.replace_all("-", "_", literal=True)
        out.append(("ID 하이픈 표기", s.str.contains("-", literal=True)))
        out.append(("더미 ID(_999999999)", v.str.ends_with("_999999999")))
        out.append(("ID 형식 오류", ~blank & ~v.str.contains(r"^[A-Z]{3}_\d{9}$")))
    elif col in DATES:
        v = s.str.replace_all("/", "-", literal=True)
        ok = v.str.to_datetime("%Y-%m-%d %H:%M:%S", strict=False).is_not_null() | v.str.to_date("%Y-%m-%d", strict=False).is_not_null()
        out.append(("슬래시 날짜 표기", s.str.contains("/", literal=True)))
        out.append(("존재하지 않는 날짜/형식 오류", ~blank & ~ok))
    elif col in NUMERIC:
        n = s.cast(pl.Int64, strict=False)
        out.append(("음수 값", n < 0))
        out.append(("숫자 아님", ~blank & n.is_null()))
    elif col in STD:
        out.append(("코드 별칭 표기(복구 가능)", s.is_in(list(ALIAS.get(col, set())))))
        out.append(("미등록 코드", ~blank & ~s.is_in(list(STD[col] | ALIAS.get(col, set())))))
    elif col in NAMES:
        out.append(("길이 초과", s.str.len_chars() > NAMES[col]))
    return out


defects, rows = [], []
for t in TABLES:
    d = read(t)
    d = d.with_columns(pl.col("source_system").str.strip_chars().alias("_src"))
    flags = []
    for col in d.columns:
        if col in SKIP_COLS or col == "_src":
            continue
        for name, cond in checks(t, col):
            fname = f"{col}|{name}"
            d = d.with_columns(cond.fill_null(False).alias(fname))
            flags.append(fname)
    names = [c for c in d.columns if c not in flags and c != "_src"]
    d = d.with_columns((~pl.struct(names).is_first_distinct()).alias("_|완전 중복 행"))
    flags.append("_|완전 중복 행")
    d = d.with_columns(pl.any_horizontal(flags).alias("_any"))
    agg = d.group_by("_src").agg([pl.len().alias("rows"), pl.col("_any").sum().alias("defect_rows")] +
                                 [pl.col(f).sum().alias(f) for f in flags])
    for r in agg.iter_rows(named=True):
        rows.append(dict(table=t, source_system=r["_src"], rows=r["rows"], defect_rows=r["defect_rows"]))
        for f in flags:
            if r[f]:
                col, typ = f.split("|", 1)
                defects.append(dict(table=t, source_system=r["_src"], column=col, defect_type=typ, n=r[f]))
    print(t, "done", flush=True)

R = pl.DataFrame(rows).with_columns((pl.col("defect_rows") / pl.col("rows") * 100).round(3).alias("defect_pct")).sort(["table", "source_system"])
D = pl.DataFrame(defects).sort(["table", "column", "defect_type", "source_system"])
R.write_csv(os.path.join(OUT, "bronze_rows_by_source.csv"), include_bom=True)
D.write_csv(os.path.join(OUT, "bronze_defects_by_source.csv"), include_bom=True)
with pl.Config(tbl_rows=200, tbl_width_chars=200, fmt_str_lengths=40):
    print(R)
    print(D.group_by(["defect_type", "source_system"]).agg(pl.col("n").sum()).pivot(on="source_system", index="defect_type", values="n").sort("defect_type"))
