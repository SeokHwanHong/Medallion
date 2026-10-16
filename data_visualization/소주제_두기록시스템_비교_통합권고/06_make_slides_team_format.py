# -*- coding: utf-8 -*-
"""
[황유민] 팀 발표 틀(1 개요 / 2 데이터 / 3 분석 / 4 결론)에 맞춘 발표 자료(16:9) 생성 - 두 기록 시스템(LEGACY_A/B) 비교와 통합 권고.
  04_make_slides.py 의 데이터·차트 부분을 그대로 쓰고 슬라이드 구성만 다르다. 추가 입력: ../분석초안/out/02_scan.txt(Q01), out/bronze_*.csv, ../정제결과/report/정제_요약.csv
- 데이터 출처: DB(team3_medallion, team3_medallion_dq) 조회 결과 텍스트. 모두 조회 전용 세션에서 SELECT 만 실행.
    ../분석초안/out/05_source.txt (S01, S03), 06_rank.txt (S15, S16), 07_master.txt (M01~M05), 08_facts.txt (F01~F06)
  단, 원본 단가표 오류의 파급(슬라이드 7 왼쪽)은 DB 에 원본(Bronze)이 없어 원본 CSV 에서 계산한다(화면에 '원본 기준' 표시).
- 출력: out/charts/d_*.png (슬라이드 차트), 발표자료_팀포맷_원천시스템_통합.pdf
실행: python -I 06_make_slides_team_format.py <원본 data 폴더>
"""
import glob
import os
import re
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import polars as pl
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas
from reportlab.platypus import Paragraph

DATA = sys.argv[1] if len(sys.argv) > 1 else os.path.join("..", "data")
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DBOUT = os.path.join(BASE, "..", "분석초안", "out")
CH = os.path.join(BASE, "out", "charts")
PDF = os.path.join(BASE, "발표자료_팀포맷_원천시스템_통합.pdf")
os.makedirs(CH, exist_ok=True)


# ------------------------------------------------------------------ DB 조회 결과 읽기
def parse(path):
    """'## 코드' 구간별 표를 {코드: [행 dict]} 로 읽는다."""
    res, cur, header = {}, None, None
    for line in open(path, encoding="utf-8"):
        m = re.search(r"## ([A-Z]\d+)", line)
        if m:
            cur, header = m.group(1), None
            res[cur] = []
            continue
        if cur is None or not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if header is None:
            header = cells
        elif cells != header and len(cells) == len(header):
            res[cur].append(dict(zip(header, cells)))
    return res


DB = {}
for f in ("05_source.txt", "06_rank.txt", "07_master.txt", "08_facts.txt"):
    DB.update(parse(os.path.join(DBOUT, f)))
I = lambda x: int(float(x))

# 인사이트 1: 직접 결함(재정제 격리 중 direct) A/B
direct = {}
for r in DB["F01"]:
    if r["quarantine_kind"] == "direct":
        direct.setdefault(r["table_name"], {})[r["src"]] = I(r["n"])
# 인사이트 2: 기준정보 원천
master = {}
for r in DB["F03"]:
    master.setdefault(r["t"], {})[r["src"]] = I(r["n"])
same_map = DB["F04"][0]
# 인사이트 3: 병원 원천, 진료 흐름 일치
hosp = {r["src"]: I(r["n"]) for r in DB["S01"] if r["t"] == "hospitals"}
chain = {r["all_same"]: I(r["n"]) for r in DB["S03"]}
chain_total = sum(chain.values())
chain_same_pct = chain.get("1", 0) / chain_total * 100
# 인사이트 4: 환자 교차
pt = {r["patient_src"]: r for r in DB["S15"]}
both = sum(I(v["both_ab"]) for v in pt.values())
pts = sum(I(v["patients"]) for v in pt.values())
both_pct = both / pts * 100
ck = DB["S16"]
ck_total = sum(I(r["n"]) for r in ck)
ck_cross = sum(I(r["n"]) for r in ck if r["checkin_src"] != r["patient_src"])
ck_cross_pct = ck_cross / ck_total * 100
# 인사이트 5: 예약 미이행 비율과 시각
st = {(r["src"], r["status"]): (I(r["n"]), float(r["pct"])) for r in DB["F06"]}
ev = {(r["src"], r["event_type"]): r for r in DB["F05"]}
a_cancel_pct, b_noshow_pct = st[("LEGACY_A", "CANCELLED")][1], st[("LEGACY_B", "NO_SHOW")][1]
a_ev, b_ev = ev[("LEGACY_A", "CANCELLED")], ev[("LEGACY_B", "NO_SHOW")]
# 추천 1: Silver 연결 무결성
link = {r["source_system"]: r for r in DB["M04"]}
dept = DB["M05"]
cat = DB["M01"][0]


# 인사이트 7: 원본 단가표(A) 오류 → A/B 진료 서비스 줄 (원본 CSV, 완전 중복 행만 제거)
def rd(t):
    fs = [f for f in sorted(glob.glob(os.path.join(DATA, t, "*.csv"))) if not os.path.basename(f).startswith("~$")]
    return pl.concat([pl.read_csv(f, infer_schema=False) for f in fs]).unique()


nid = lambda c: pl.col(c).str.strip_chars().str.replace_all("-", "_", literal=True)
scb = rd("service_catalog")
neg_keys = scb.filter(pl.col("unit_price").str.strip_chars().cast(pl.Int64, strict=False) < 0).select(nid("service_version_id"))["service_version_id"].to_list()
hyp_keys = scb.filter(pl.col("service_version_id").str.contains("-", literal=True)).select(nid("service_version_id"))["service_version_id"].to_list()
esb = rd("encounter_services").select(nid("service_version_id").alias("k"), pl.col("source_system").str.strip_chars().alias("src"))
prop = {}
for name, keys in (("neg", neg_keys), ("hyp", hyp_keys)):
    prop[name] = {r["src"]: r["len"] for r in esb.filter(pl.col("k").is_in(keys)).group_by("src").len().iter_rows(named=True)}
bad_rows = len(neg_keys) + len(hyp_keys)
lines_a = prop["neg"].get("LEGACY_A", 0) + prop["hyp"].get("LEGACY_A", 0)
lines_b = prop["neg"].get("LEGACY_B", 0) + prop["hyp"].get("LEGACY_B", 0)
lines_all = lines_a + lines_b
print("prop", prop, bad_rows, lines_a, lines_b, lines_all, scb.height)

# ------------------------------------------------------------------ 색 (A=파랑, B=주황: 검증된 범주 팔레트 1·2번)
A, B = "#2a78d6", "#eb6834"
INK, MUTED, GRID, SURF, NEUTRAL = "#0b0b0b", "#52514e", "#e4e3df", "#ffffff", "#8a8984"
NAVY, SOFT, GOOD = "#16324f", "#f3f6fa", "#1f7a4d"
plt.rcParams["font.family"] = "Malgun Gothic"
plt.rcParams["axes.unicode_minus"] = False


def clean(ax):
    ax.set_facecolor(SURF)
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)
    ax.spines["bottom"].set_color(GRID)
    ax.tick_params(colors=MUTED, length=0, labelsize=11)


# d1) 직접 결함 건수 A/B (DB)
order = [("appointment_events", "예약 이력"), ("encounter_services", "진료 서비스"), ("checkins", "접수"),
         ("appointments", "예약"), ("payments", "결제"), ("patients", "환자")]
fig, ax = plt.subplots(figsize=(8.6, 4.8), facecolor=SURF)
x = np.arange(len(order))
w = 0.36
av = [direct[t]["LEGACY_A"] for t, _ in order]
bv = [direct[t]["LEGACY_B"] for t, _ in order]
ax.bar(x - w / 2 - 0.02, av, w, color=A, label="LEGACY_A")
ax.bar(x + w / 2 + 0.02, bv, w, color=B, label="LEGACY_B")
for i in range(len(order)):
    ax.text(x[i] - w / 2 - 0.02, av[i] + 600, f"{av[i]:,}", ha="center", va="bottom", fontsize=9, color=INK, rotation=90)
    ax.text(x[i] + w / 2 + 0.02, bv[i] + 600, f"{bv[i]:,}", ha="center", va="bottom", fontsize=9, color=INK, rotation=90)
ax.set_xticks(x, [n for _, n in order], fontsize=11.5, color=INK)
ax.set_yticks([])
ax.set_ylim(0, max(av + bv) * 1.32)
clean(ax)
ax.legend(frameon=False, fontsize=11, loc="upper right", ncol=2)
ax.set_title("시스템 자체 결함으로 격리된 행 수 (연쇄 격리 제외)", fontsize=12, color=MUTED, loc="left")
fig.tight_layout()
fig.savefig(os.path.join(CH, "d_direct_defects.png"), dpi=180)
plt.close(fig)

# d2) 환자 교차 이용 (DB): 등록 시스템 구분 없이 전체 환자 막대 하나
fig, ax = plt.subplots(figsize=(8.6, 3.2), facecolor=SURF)
left = 0.0
for colname, lab, colr in (("only_a", "A 병원만", A), ("both_ab", "A·B 둘 다", NEUTRAL), ("only_b", "B 병원만", B)):
    n = sum(I(pt[s][colname]) for s in ("LEGACY_A", "LEGACY_B"))
    v = n / pts * 100
    ax.barh([0], [v], left=left, color=colr, edgecolor=SURF, linewidth=2, height=0.6)
    ax.text(left + v / 2, 0, f"{lab}\n{v:.1f}%\n({n:,}명)", ha="center", va="center", fontsize=12.5, color="#ffffff", fontweight="bold")
    left += v
ax.set_xlim(0, 100)
ax.set_ylim(-0.45, 0.45)
clean(ax)
ax.set_yticks([])
ax.set_xticks([])
ax.spines["bottom"].set_visible(False)
ax.set_title(f"예약한 환자 {pts:,}명이 이용한 병원", fontsize=12.5, color=MUTED, loc="left")
fig.tight_layout()
fig.savefig(os.path.join(CH, "d_patient_cross.png"), dpi=180)
plt.close(fig)

# d3) 예약 미이행이 기록되는 시점 (DB)
fig, ax = plt.subplots(figsize=(9.6, 3.6), facecolor=SURF)
ax.axvline(0, color=INK, linewidth=1.5)
ax.text(0, 2.05, "예약 시각", ha="center", fontsize=12, color=INK, fontweight="bold")
ax.axvspan(-4, 0, color="#eef4fb")
ax.text(-2.0, 1.83, "예약 전", ha="center", fontsize=12, color=MUTED)
ax.text(2.0, 1.83, "예약 후", ha="center", fontsize=12, color=MUTED)
a_min, b_min = I(a_ev["min_min"]) / 60, I(b_ev["min_min"]) / 60
ax.scatter([a_min], [1.2], s=520, color=A, zorder=3)
ax.scatter([b_min], [0.55], s=520, color=B, zorder=3)
ax.text(a_min, 1.2 - 0.30, f"A 병원: 취소 {I(a_ev['n']):,}건\n전부 예약 {abs(a_min):.0f}시간 전", ha="center", va="top", fontsize=13, color=INK)
ax.text(b_min, 0.55 + 0.30, f"B 병원: 노쇼 {I(b_ev['n']):,}건\n전부 예약 {b_min:.0f}시간 뒤", ha="center", va="bottom", fontsize=13, color=INK)
ax.set_xlim(-4, 4)
ax.set_ylim(0, 2.25)
ax.set_xticks([-4, -3, -2, -1, 0, 1, 2, 3, 4], ["-4h", "-3h", "-2h", "-1h", "0", "+1h", "+2h", "+3h", "+4h"], fontsize=10.5)
ax.set_yticks([])
clean(ax)
fig.tight_layout()
fig.savefig(os.path.join(CH, "d_unmet_timing.png"), dpi=180)
plt.close(fig)

# ------------------------------------------------------------------ 슬라이드
pdfmetrics.registerFont(TTFont("MG", "C:/Windows/Fonts/malgun.ttf"))
pdfmetrics.registerFont(TTFont("MGB", "C:/Windows/Fonts/malgunbd.ttf"))
pdfmetrics.registerFontFamily("MG", normal="MG", bold="MGB", italic="MG", boldItalic="MGB")
W, H = 960, 540
c = canvas.Canvas(PDF, pagesize=(W, H))
c.setTitle("두 기록 시스템, 하나로 합치기 전에 확인할 것")
c.setAuthor("황유민")
PAGE = [0]
TOTAL = 21


def P(size=16, color=INK, bold=False, leading=None):
    return ParagraphStyle("p", fontName="MGB" if bold else "MG", fontSize=size, leading=leading or size * 1.45,
                          textColor=colors.HexColor(color), alignment=TA_LEFT)


def para(text, x, y_top, w, style):
    p = Paragraph(text, style)
    _, h = p.wrap(w, H)
    p.drawOn(c, x, y_top - h)
    return y_top - h


def slide(title, section=None, dark=False, source=None):
    if PAGE[0] > 0:
        c.showPage()
    PAGE[0] += 1
    c.setFillColor(colors.HexColor(NAVY if dark else SURF))
    c.rect(0, 0, W, H, stroke=0, fill=1)
    if dark:
        return
    c.setFillColor(colors.HexColor(NAVY))
    c.rect(0, H - 6, W, 6, stroke=0, fill=1)
    c.setFont("MGB", 26)
    c.setFillColor(colors.HexColor(INK))
    c.drawString(48, H - 82, title)
    c.setFont("MG", 9.5)
    c.setFillColor(colors.HexColor(MUTED))
    c.drawString(48, 20, "두 기록 시스템(LEGACY_A / LEGACY_B) 비교 · 황유민")
    c.drawRightString(W - 48, 20, f"{PAGE[0]} / {TOTAL}")
    if source:
        c.drawString(48, 34, "출처: " + source)


def image(name, x, y, w, h):
    path = os.path.join(CH, name)
    iw, ih = ImageReader(path).getSize()
    s = min(w / iw, h / ih)
    dw, dh = iw * s, ih * s
    c.drawImage(path, x + (w - dw) / 2, y + (h - dh) / 2, dw, dh)


def card(x, y, w, h, big, small, color=NAVY, big_size=28):
    c.setFillColor(colors.HexColor(SOFT))
    c.roundRect(x, y, w, h, 10, stroke=0, fill=1)
    c.setFillColor(colors.HexColor(color))
    c.roundRect(x, y, 6, h, 3, stroke=0, fill=1)
    c.setFont("MGB", big_size)
    c.drawString(x + 22, y + h - 18 - big_size, big)
    para(small, x + 22, y + h - 30 - big_size, w - 36, P(13, MUTED, leading=18))


def box(x, y, w, h, title, body, color=NAVY, size=14):
    c.setFillColor(colors.HexColor(SOFT))
    c.roundRect(x, y, w, h, 10, stroke=0, fill=1)
    c.setFillColor(colors.HexColor(color))
    c.setFont("MGB", 15)
    c.drawString(x + 18, y + h - 30, title)
    para(body, x + 18, y + h - 42, w - 36, P(size, INK, leading=size * 1.5))


def takeaway(text, y=58, h=44):
    c.setFillColor(colors.HexColor(NAVY))
    c.roundRect(48, y, W - 96, h, 8, stroke=0, fill=1)
    para(text, 66, y + h - 11, W - 132, P(15, "#ffffff", bold=True, leading=21))


def arrow(x1, y1, x2, y2, color=MUTED):
    c.setStrokeColor(colors.HexColor(color))
    c.setFillColor(colors.HexColor(color))
    c.setLineWidth(2.5)
    c.line(x1, y1, x2 - 10, y2)
    p = c.beginPath()
    p.moveTo(x2, y2)
    p.lineTo(x2 - 12, y2 + 7)
    p.lineTo(x2 - 12, y2 - 7)
    p.close()
    c.drawPath(p, stroke=0, fill=1)


max_gap = max(abs(direct[t]["LEGACY_A"] - direct[t]["LEGACY_B"]) / max(direct[t]["LEGACY_A"], direct[t]["LEGACY_B"]) * 100 for t, _ in order)

# ------------------------------------------------------------------ 팀 발표 틀 추가 데이터
q01 = parse(os.path.join(DBOUT, "02_scan.txt"))["Q01"]
silver_rows = {r["t"]: I(r["n"]) for r in q01}
silver_rows.update({"code_dictionary": master["code_dictionary"].get("LEGACY_A", 0),
                    "legacy_code_mappings": sum(master["legacy_code_mappings"].values())})
br = pl.read_csv(os.path.join(BASE, "out", "bronze_rows_by_source.csv")).group_by("table").agg(pl.col("rows").sum())
bronze_rows = {r["table"]: r["rows"] for r in br.iter_rows(named=True)}
bronze_rows.update({"code_dictionary": 36, "legacy_code_mappings": 72})
bronze_total = sum(bronze_rows.values())
silver_total = sum(silver_rows.values())
dfx = pl.read_csv(os.path.join(BASE, "out", "bronze_defects_by_source.csv")).group_by("defect_type").agg(pl.col("n").sum()).sort("n", descending=True)
defect = {r["defect_type"]: r["n"] for r in dfx.iter_rows(named=True)}
mine = pl.read_csv(os.path.join(BASE, "..", "정제결과", "report", "정제_요약.csv"), encoding="utf8-lossy")
mine = mine.rename({mine.columns[0]: "table"})
n_csv = len([f for f in glob.glob(os.path.join(DATA, "*", "*.csv")) if not os.path.basename(f).startswith("~$")])
print("bronze", bronze_total, "silver", silver_total, "csv", n_csv)


def table_rows(x, y_top, col_w, header, rows, size=12.5, row_h=24, head_fill=NAVY, zebra=True, aligns=None):
    """간단한 표: header(list), rows(list of list). x,y_top 기준 왼쪽 위."""
    aligns = aligns or ["l"] + ["r"] * (len(header) - 1)
    w = sum(col_w)
    c.setFillColor(colors.HexColor(head_fill))
    c.rect(x, y_top - row_h, w, row_h, stroke=0, fill=1)
    c.setFillColor(colors.HexColor("#ffffff"))
    c.setFont("MGB", size)
    cx = x
    for h_, cw_, al in zip(header, col_w, aligns):
        if al == "l":
            c.drawString(cx + 8, y_top - row_h + 7, h_)
        else:
            c.drawRightString(cx + cw_ - 8, y_top - row_h + 7, h_)
        cx += cw_
    y = y_top - row_h
    for i, r in enumerate(rows):
        if zebra and i % 2 == 0:
            c.setFillColor(colors.HexColor(SOFT))
            c.rect(x, y - row_h, w, row_h, stroke=0, fill=1)
        cx = x
        for j, (v, cw_, al) in enumerate(zip(r, col_w, aligns)):
            bold = isinstance(v, tuple)
            txt = v[0] if bold else v
            col = v[1] if bold and len(v) > 1 else INK
            c.setFillColor(colors.HexColor(col))
            c.setFont("MGB" if bold else "MG", size)
            if al == "l":
                c.drawString(cx + 8, y - row_h + 7, str(txt))
            else:
                c.drawRightString(cx + cw_ - 8, y - row_h + 7, str(txt))
            cx += cw_
        y -= row_h
    return y


def section_cover(num, title, items):
    slide("", dark=True)
    c.setFillColor(colors.HexColor("#ffb48f"))
    c.setFont("MGB", 60)
    c.drawString(70, 330, num)
    c.setFillColor(colors.HexColor("#ffffff"))
    c.setFont("MGB", 38)
    c.drawString(70, 270, title)
    c.setFillColor(colors.HexColor("#d6e2ef"))
    c.setFont("MG", 17)
    yy = 220
    for it in items:
        c.drawString(72, yy, it)
        yy -= 30


# ================================================================== 슬라이드
# 표지
slide("", dark=True)
c.setFillColor(colors.HexColor("#9fb7d3"))
c.setFont("MGB", 14)
c.drawString(70, 380, "병원 진료 및 수납 시스템 최적화")
para("두 기록 시스템,<br/>하나로 합치기 전에 확인할 것", 70, 360, 820, P(40, "#ffffff", True, 54))
para("레거시 데이터 정제 · DB 적재 · LEGACY_A / LEGACY_B 비교와 통합 권고", 70, 228, 820, P(18, "#d6e2ef", leading=26))
c.setFont("MG", 14)
c.setFillColor(colors.HexColor("#d6e2ef"))
c.drawString(70, 90, "황유민  ·  Medallion(Bronze → Silver → Gold)  ·  데이터: team3_medallion DB")

# 목차
slide("목차")
toc = [("1", "개요", "대주제와 소주제"),
       ("2", "데이터", "데이터 소개 · 정제(Cleaning) · DB 적재와 정합성"),
       ("3", "분석", "대주제 AS-IS · 소주제 분석 · 결과 종합"),
       ("4", "결론", "To-Be · 요약과 한계 · 보완점")]
yy = 430
for n, t, d in toc:
    c.setFillColor(colors.HexColor(SOFT))
    c.roundRect(48, yy - 70, 864, 72, 10, stroke=0, fill=1)
    c.setFillColor(colors.HexColor(NAVY))
    c.setFont("MGB", 34)
    c.drawString(72, yy - 50, n)
    c.setFont("MGB", 22)
    c.drawString(130, yy - 44, t)
    c.setFillColor(colors.HexColor(MUTED))
    c.setFont("MG", 15)
    c.drawString(260, yy - 43, d)
    yy -= 88

# ---------------------------------------------------------------- 1. 개요
slide("1. 개요")
box(48, 330, 864, 112, "대주제 · 병원 진료 및 수납 시스템 최적화",
    "레거시 병원 데이터는 결측·중복·형식 불일치·코드 혼용으로 오염돼 있고, 서로 다른 기록 시스템(LEGACY_A / B)에 나뉘어 있습니다. "
    "<b>이 데이터를 정제해 믿을 수 있는 지표를 만들고, 진료·수납 운영을 개선할 근거를 찾는 것</b>이 문제 제기입니다.", NAVY, size=14.5)
para("<b>소주제 (관점)</b>", 48, 312, 864, P(16, NAVY, True))
subs = [("관점 1", "병원별 환자 밀집도 분석을 통한 의사 진료 배치 최적화", False),
        ("관점 2", "진료 후 결제·환불 패턴 분석을 통한 병원 재정 관리 및 수납 업무 효율화", False),
        ("관점 3", "환자군별 예약·방문 이행 패턴 분석을 통한 진료 수요 파악", False),
        ("관점 4", "두 기록 시스템(LEGACY_A / B) 비교를 통한 통합 권고  ← 본 발표", True)]
yy = 282
for k, t, me in subs:
    c.setFillColor(colors.HexColor("#fff1ea" if me else SOFT))
    c.roundRect(48, yy - 40, 864, 42, 8, stroke=0, fill=1)
    c.setFillColor(colors.HexColor(B if me else MUTED))
    c.setFont("MGB", 14)
    c.drawString(66, yy - 25, k)
    c.setFillColor(colors.HexColor(INK))
    c.setFont("MGB" if me else "MG", 14.5)
    c.drawString(150, yy - 25, t)
    yy -= 50

# ---------------------------------------------------------------- 2. 데이터
section_cover("2", "데이터", ["2.1 데이터 소개", "2.2 Cleaning: 정제 로직과 도구", "2.3 Cleaning 결과: DB 적재와 정합성 검토"])

# 2.1 데이터 소개
slide("2.1 데이터 소개", source="받은 원본 CSV, 명세서(hospital_명세서.xlsx)")
card(48, 352, 270, 100, f"{bronze_total / 10000:,.0f}만 행", "상대 팀이 만든 레거시 병원 데이터", NAVY, big_size=28)
card(345, 352, 270, 100, "17개 테이블", f"CSV {n_csv}개 (월별 분할 포함)", A, big_size=28)
card(642, 352, 270, 100, "2023~2025", "3년치 예약·접수·진료·수납 기록", B, big_size=28)
para("<b>업무 흐름 (데이터 구조)</b>", 48, 336, 864, P(15, NAVY, True))
flow = ["병원·의사", "진료 운영 구간", "예약 시간대", "예약", "접수", "진료", "진료 서비스", "결제"]
bx, bw, gap = 48, 96, 13.7
for i, f_ in enumerate(flow):
    x0 = bx + i * (bw + gap)
    c.setFillColor(colors.HexColor(NAVY if i in (4, 5, 7) else "#5b7a99"))
    c.roundRect(x0, 266, bw, 42, 7, stroke=0, fill=1)
    para(f"<font color='#ffffff'><b>{f_}</b></font>", x0 + 6, 300, bw - 12, P(11.5, "#ffffff", True, 15))
    if i < len(flow) - 1:
        c.setFillColor(colors.HexColor(MUTED))
        c.setFont("MGB", 12)
        c.drawCentredString(x0 + bw + gap / 2, 282, "›")
groups = [["기준정보", "병원 · 진료과 · 병원별 진료과 · 의사 · 의사 배치 · 환자", f"{sum(bronze_rows[t] for t in ('hospitals', 'departments', 'hospital_departments', 'doctors', 'doctor_assignments', 'patients')):,}"],
          ["코드·단가", "표준 코드 사전 · 원천 코드 매핑 · 서비스 단가표", f"{sum(bronze_rows[t] for t in ('code_dictionary', 'legacy_code_mappings', 'service_catalog')):,}"],
          ["운영·예약", "진료 운영 구간 · 예약 시간대 · 예약 · 예약 이력", f"{sum(bronze_rows[t] for t in ('clinic_sessions', 'appointment_slots', 'appointments', 'appointment_events')):,}"],
          ["접수·진료·수납", "접수 · 진료 · 진료 서비스 · 결제", f"{sum(bronze_rows[t] for t in ('checkins', 'encounters', 'encounter_services', 'payments')):,}"]]
table_rows(48, 250, [130, 584, 150], ["구분", "테이블", "행 수"], groups, size=13, row_h=25, aligns=["l", "l", "r"])
c.setFont("MG", 11)
c.setFillColor(colors.HexColor(MUTED))
c.drawString(48, 104, "모든 테이블에 source_system(LEGACY_A / LEGACY_B) 컬럼이 있어, 기록이 어느 레거시 시스템에서 왔는지 남아 있습니다.")

# 2.2 정제 로직
slide("2.2 Cleaning: 정제 로직", source="명세서 업무 규칙 B14·B15·B16, 정제결과/report/정제_판단근거_리포트")
cols3 = [("복구", "의미가 바뀌지 않는 표기 차이만 고친다",
          "• ID 하이픈 → 밑줄 (PAT-1 → PAT_1)<br/>• 슬래시 날짜 → 표준 형식<br/>• 앞뒤 공백 제거<br/>• 등록된 한글 별칭 → 표준 코드 (취소 → CANCELLED)", GOOD),
         ("격리", "복구 근거가 없으면 추측하지 않고 따로 보관",
          "• 필수값 결측 · 더미 ID(…_999999999)<br/>• 존재하지 않는 날짜(2024-02-30)<br/>• 미등록 코드(UNREGISTERED) · 음수<br/>• 원본 값 + 사유 코드 + 복구 힌트 보존", B),
         ("제외", "모든 값이 같은 재전송 행은 하나만 남긴다",
          f"• 완전 중복 행 (전체 {defect['완전 중복 행']:,}행)<br/>• 값이 하나라도 다르면 제외하지 않고<br/>&nbsp;&nbsp;PK 중복으로 격리해 사람이 판단", A)]
for i, (t, sub, body, col) in enumerate(cols3):
    x0 = 48 + i * 298
    c.setFillColor(colors.HexColor(SOFT))
    c.roundRect(x0, 150, 268, 300, 10, stroke=0, fill=1)
    c.setFillColor(colors.HexColor(col))
    c.rect(x0, 444, 268, 6, stroke=0, fill=1)
    c.setFont("MGB", 24)
    c.drawString(x0 + 18, 404, t)
    para(sub, x0 + 18, 392, 236, P(13, MUTED, leading=19))
    para(body, x0 + 18, 340, 240, P(13.5, INK, leading=24))
takeaway("규칙: 부모 → 자식 순서로 처리하고, 부모가 격리돼 함께 빠진 행은 '연쇄 격리'로 따로 표시 · 수신 = 정제본 + 격리 + 제외 로 건수 대사", 82, 50)

# 2.2 도구
slide("2.2 Cleaning: 왜 Python + Polars 인가", source="정제결과/scripts, 정제결과/notebooks")
reasons = [("대용량을 빠르게", f"원본 약 {bronze_total / 10000:,.0f}만 행. 멀티스레드·컬럼 기반이라 담당 5개 테이블(약 273만 행)을 약 20초에 정제"),
           ("형 변환 오류까지 잡기", "모든 컬럼을 문자열로 읽고 직접 변환 → 자동 추론이 숨기는 '2024-02-30', '숫자 칸의 문자'를 결함으로 집계"),
           ("규칙을 그대로 코드로", "표현식(Expression)으로 '복구 / 격리 사유 / 연쇄' 규칙을 선언적으로 작성 → 규칙표와 코드가 1:1"),
           ("재현과 검증", "같은 입력이면 같은 결과. 테이블별 노트북으로 나눴고, 정제는 Polars 로만 하고 결과 건수는 pandas 로 따로 다시 계산해 일치 확인")]
yy = 446
for t, d in reasons:
    c.setFillColor(colors.HexColor(SOFT))
    c.roundRect(48, yy - 76, 864, 78, 10, stroke=0, fill=1)
    c.setFillColor(colors.HexColor(A))
    c.roundRect(48, yy - 76, 6, 78, 3, stroke=0, fill=1)
    c.setFillColor(colors.HexColor(INK))
    c.setFont("MGB", 17)
    c.drawString(72, yy - 30, t)
    para(d, 72, yy - 40, 820, P(13.5, MUTED, leading=20))
    yy -= 90

# 2.3 결과: 담당 테이블
slide("2.3 Cleaning 결과 (담당 5개 테이블)", source="정제결과/report/정제_요약.csv (Polars 정제, pandas 독립 재계산 일치)")
ko = {"doctors": "의사", "doctor_assignments": "의사 배치", "clinic_sessions": "진료 운영 구간", "appointment_slots": "예약 시간대", "checkins": "접수"}
rows_m = []
for r in mine.iter_rows(named=True):
    vals = list(r.values())
    t, recv, exc, qd, qc, cl = vals[0], vals[1], vals[2], vals[3], vals[4], vals[5]
    ok = recv == exc + qd + qc + cl
    rows_m.append([f"{ko.get(t, t)} ({t})", f"{recv:,}", f"{exc:,}", f"{qd:,}", f"{qc:,}", (f"{cl:,}",), (("일치" if ok else "불일치"), GOOD if ok else B)])
table_rows(48, 446, [250, 110, 90, 110, 110, 110, 84], ["테이블", "수신", "제외(중복)", "격리(직접)", "격리(연쇄)", "정제본", "대사"], rows_m, size=13, row_h=32)
box(48, 110, 420, 140, "검증", "• 수신 = 제외 + 격리 + 정제본, 5개 테이블 모두 일치<br/>• 정제본에 같은 규칙을 다시 적용 → 위반 0건<br/>• pandas 로 독립 재계산 → 건수 일치", GOOD, size=14)
box(492, 110, 420, 140, "연쇄 격리가 많은 이유",
    "의사 252명 격리 → 배치 756건 → 운영 구간 → 예약 시간대·접수로 이어집니다. 연쇄 행은 자기 값에는 문제가 없어, 부모가 복구되면 되살릴 수 있습니다.", B, size=13.5)

# 2.3 결과: DB 적재와 정합성
slide("2.3 DB 적재와 정합성 검토", source="team3_medallion(Silver), team3_medallion_dq(격리·재정제 기록) 조회 결과")
order_t = ["hospitals", "departments", "hospital_departments", "doctors", "doctor_assignments", "patients", "code_dictionary",
           "legacy_code_mappings", "service_catalog", "clinic_sessions", "appointment_slots", "appointments", "appointment_events",
           "checkins", "encounters", "encounter_services", "payments"]
rows_db = [[t, f"{bronze_rows[t]:,}", f"{silver_rows[t]:,}", f"{silver_rows[t] / bronze_rows[t] * 100:.1f}%"] for t in order_t]
rows_db.append([("합계",), (f"{bronze_total:,}",), (f"{silver_total:,}",), (f"{silver_total / bronze_total * 100:.1f}%",)])
table_rows(48, 440, [190, 100, 100, 70], ["테이블", "원본", "DB(Silver)", "남은 비율"], rows_db, size=10.5, row_h=18.5)
c.setFillColor(colors.HexColor("#eef7f1"))
c.roundRect(540, 98, 372, 342, 10, stroke=0, fill=1)
c.setFillColor(colors.HexColor(GOOD))
c.setFont("MGB", 15)
c.drawString(558, 412, "DB 정합성 검토 (team3_medallion)")
checks2 = [("진료 서비스 → 단가표 연결 오류", "0줄"), ("단가 불일치 · 유효기간 밖 버전", "0줄"), ("병원별 진료과·의사 → 진료과 연결 오류", "0건"),
           ("진료 흐름(병원~진료) 시스템 일치", f"{chain_same_pct:.0f}%"), ("원천 코드 매핑 A·B 일치", f"{same_map['same_in_b']}/{same_map['a_rows']}"),
           ("단가표 음수 단가 · ID 표기 오류", "0행")]
yy = 380
for name, v in checks2:
    c.setFillColor(colors.HexColor(INK))
    c.setFont("MG", 13)
    c.drawString(558, yy, name)
    c.setFillColor(colors.HexColor(GOOD))
    c.setFont("MGB", 15)
    c.drawRightString(894, yy, v)
    yy -= 36
para("격리·제외된 행은 team3_medallion_dq 에 사유 코드와 함께 보관합니다.", 558, 156, 340, P(12.5, MUTED, leading=18))

# ---------------------------------------------------------------- 3. 분석
section_cover("3", "분석", ["3.1 대주제 소개: AS-IS", "3.2 소주제 소개 및 분석", "3.3 결과 종합"])

# 3.1 AS-IS
slide("3.1 대주제 AS-IS: 현재의 문제점", source="받은 원본 CSV 전수 집계, team3_medallion")
para("<b>문제 ① 데이터를 그대로 믿을 수 없다</b>", 48, 446, 430, P(16, B, True))
top = [("더미 ID (…_999999999)", "더미 ID(_999999999)"), ("필수값 결측", "결측(필수값 빈칸)"), ("ID 하이픈 표기", "ID 하이픈 표기"),
       ("미등록 코드 (UNREGISTERED)", "미등록 코드"), ("존재하지 않는 날짜", "존재하지 않는 날짜/형식 오류"), ("음수 값", "음수 값"),
       ("완전 중복 행", "완전 중복 행")]
table_rows(48, 418, [290, 130], ["결함 유형", "건수"], [[a, f"{defect[k]:,}"] for a, k in top], size=13, row_h=27)
para("결함 행을 걸러낸 뒤에야 지표를 계산할 수 있습니다.", 48, 186, 420, P(13, MUTED, leading=19))
para("<b>문제 ② 기록이 두 시스템에 나뉘어 있다</b>", 492, 446, 420, P(16, B, True))
box(492, 260, 420, 168, "LEGACY_A / LEGACY_B",
    f"• 모든 기록에 출처 표시(source_system)가 있습니다<br/>• 병원 {hosp['LEGACY_A'] + hosp['LEGACY_B']}곳이 A {hosp['LEGACY_A']}곳, B {hosp['LEGACY_B']}곳으로 나뉨<br/>• 같은 환자가 두 시스템 병원을 오감", NAVY, size=14)
box(492, 150, 420, 96, "그래서 묻는 질문", "두 시스템 중 어느 쪽이 나은가? 하나로 합쳐야 하는가?", A, size=15)

# 3.2 소주제 소개
slide("3.2 소주제: 두 기록 시스템 비교", source="명세서, team3_medallion")
box(48, 330, 864, 112, "관점",
    "LEGACY_A / B 는 모든 기록 끝에 붙은 <b>출처 표시</b>로, 기록이 원래 <b>어느 전산 시스템에 적혀 있었는지</b>를 알려 줍니다. "
    "두 시스템의 <b>품질 · 구조 · 운영 기록 · 공통 기준정보</b>를 비교해 통합이 필요한지 판단합니다.", NAVY, size=15)
qs = [("1", "품질", "두 시스템 중 데이터 결함이 더 적은 쪽이 있는가?"), ("2", "구조", "무엇이 이미 통일돼 있고, 무엇이 나뉘어 있는가?"),
      ("3", "운영", "같은 업무를 같은 방식으로 기록하는가?"), ("4", "기준정보", "공통 기준정보의 오류가 다른 시스템에 영향을 주는가?")]
yy = 300
for n, t, q in qs:
    c.setFillColor(colors.HexColor(NAVY))
    c.circle(66, yy - 10, 15, stroke=0, fill=1)
    c.setFillColor(colors.HexColor("#ffffff"))
    c.setFont("MGB", 14)
    c.drawCentredString(66, yy - 15, n)
    c.setFillColor(colors.HexColor(INK))
    c.setFont("MGB", 16)
    c.drawString(94, yy - 16, t)
    c.setFont("MG", 15)
    c.drawString(190, yy - 16, q)
    yy -= 44
c.setFont("MG", 11)
c.setFillColor(colors.HexColor(MUTED))
c.drawString(48, 100, "※ A/B 는 명세상 실제 제품이 아니라 '시스템이 합쳐지는 상황'을 연습하기 위한 가상 출처입니다.")

# 3.2 분석 ① 품질·구조
slide("3.2 분석 ① 품질은 같고, 기준정보는 이미 하나다", source="team3_medallion_dq.reclean_quarantine, team3_medallion 기준정보 4개 테이블")
image("d_direct_defects.png", 40, 110, 540, 350)
c.setFillColor(colors.HexColor(SOFT))
c.roundRect(600, 110, 312, 350, 10, stroke=0, fill=1)
c.setFillColor(colors.HexColor(NAVY))
c.setFont("MGB", 15)
c.drawString(618, 432, "기준정보는 전부 A 하나")
yy = 400
for name, d in (("서비스 단가표", master["service_catalog"]), ("진료과", master["departments"]), ("코드 사전", master["code_dictionary"])):
    c.setFillColor(colors.HexColor(INK))
    c.setFont("MG", 14)
    c.drawString(618, yy, name)
    c.setFont("MGB", 14)
    c.drawRightString(892, yy, f"A {d.get('LEGACY_A', 0)}행 · B {d.get('LEGACY_B', 0)}행")
    yy -= 30
c.setFont("MG", 14)
c.drawString(618, yy, "원천 코드 매핑")
c.setFont("MGB", 14)
c.drawRightString(892, yy, f"A·B {same_map['same_in_b']}/{same_map['a_rows']} 동일")
para("나뉘어 있는 것은 병원·의사·환자와 예약·접수·진료·결제 기록뿐입니다.", 618, yy - 24, 276, P(13.5, MUTED, leading=20))
takeaway("→ A/B 중 어느 쪽이 더 낫다고 말할 수 있는 근거는 없습니다.", 50)

# 3.2 분석 ② 병원·환자
slide("3.2 분석 ② 병원은 나뉘어 있고, 환자는 오간다", source="team3_medallion (hospitals, encounters~hospitals 연결, appointments, checkins, patients)")
card(48, 330, 300, 120, f"{hosp['LEGACY_A']} : {hosp['LEGACY_B']}", "A 병원 : B 병원", NAVY, big_size=30)
card(48, 192, 300, 124, f"{chain_same_pct:.0f}%", f"진료 {chain_total:,}건 중 병원·구간·접수·진료가<br/>같은 시스템인 비율 (한 병원 = 한 시스템)", NAVY, big_size=30)
para("그래서 A/B 비교는 곧 <b>병원군 비교</b>입니다. 차이가 시스템 때문인지 병원 특성 때문인지는 구분할 수 없습니다.", 48, 176, 300, P(12.5, MUTED, leading=18))
image("d_patient_cross.png", 362, 150, 550, 300)
para(f"예약한 환자의 <b>{both_pct:.1f}%</b>가 A·B 병원을 모두 이용 · 접수의 <b>{ck_cross_pct:.1f}%</b>는 다른 시스템에 등록된 환자", 380, 146, 530, P(13, INK, leading=18))
takeaway("→ 병원은 시스템별로 나뉘어 있지만 환자는 그렇지 않습니다. 환자 명단부터 하나로 합쳐야 합니다.", 50)

# 3.2 분석 ③ 운영 기록
slide("3.2 분석 ③ 같은 20%, 파악하는 시점이 다르다", source="team3_medallion.appointments, appointment_events")
cw2 = (W - 96 - 20) / 2
card(48, 342, cw2, 108, f"A {a_cancel_pct:.1f}%  ·  B {b_noshow_pct:.1f}%", "지켜지지 않은 예약 비율 (A는 전부 '취소', B는 전부 '노쇼')", NAVY, big_size=26)
card(48 + cw2 + 20, 342, cw2, 108, "2시간 전  vs  3시간 뒤", "그 사실이 기록된 시점 (예약 시각 기준)", B, big_size=26)
image("d_unmet_timing.png", 48, 116, 864, 218)
takeaway("→ A 시스템은 모든 취소를 예약 2시간 전에, B 시스템은 모든 노쇼를 예약 3시간 뒤에 파악합니다. "
         "병원 차이인지 시스템 차이인지 확정할 수는 없지만, 그 비율이 100%인 것으로 보아 시스템 차이로 추정됩니다.", 44, 64)

# 3.2 분석 ④ 기준정보
slide("3.2 분석 ④ 공통 기준정보의 작은 오류가 두 시스템에 퍼진다", source="왼쪽: 제공 데이터 원본 / 오른쪽: team3_medallion (service_catalog, encounter_services, departments)")
box(48, 270, 250, 136, "A 단가표", f"{scb.height}행 중 <b>{bad_rows}행 오류</b><br/>(음수 단가 {len(neg_keys)}행, ID 표기 오류 {len(hyp_keys)}행)", A, size=14)
arrow(304, 338, 352, 338)
box(358, 270, 250, 136, "두 시스템의 진료 서비스", f"<b>{lines_all:,}줄</b>이 오류 행을 참조<br/>A {lines_a:,}줄 · B {lines_b:,}줄", B, size=14)
para(f"단가표 1행 오류가 평균 약 {lines_all / bad_rows / 10000:.1f}만 줄에 영향 → 이 행을 격리하면 두 시스템 기록이 함께 끊깁니다.", 48, 258, 560, P(13.5, MUTED, leading=20))
c.setFillColor(colors.HexColor(GOOD))
c.setFont("MGB", 13)
c.drawString(640, 428, "정제 후 결과")
c.setFillColor(colors.HexColor("#eef7f1"))
c.roundRect(640, 110, 272, 296, 10, stroke=0, fill=1)
checks = [("단가표 오류 행", f"{I(cat['neg_price']) + I(cat['hyphen_id'])}행"),
          ("단가표에 없는 버전", f"{I(link['LEGACY_A']['not_in_catalog']) + I(link['LEGACY_B']['not_in_catalog'])}줄"),
          ("단가 불일치", f"{I(link['LEGACY_A']['price_ne_catalog']) + I(link['LEGACY_B']['price_ne_catalog'])}줄"),
          ("유효기간 밖 버전", f"{I(link['LEGACY_A']['version_out_of_period']) + I(link['LEGACY_B']['version_out_of_period'])}줄"),
          ("진료과 연결 오류", f"{sum(I(r['not_in_departments']) for r in dept)}건")]
yy = 378
for name, v in checks:
    c.setFillColor(colors.HexColor(INK))
    c.setFont("MG", 14)
    c.drawString(660, yy, name)
    c.setFillColor(colors.HexColor(GOOD))
    c.setFont("MGB", 16)
    c.drawRightString(892, yy, v)
    yy -= 38
para(f"검사 대상: 진료 서비스 A {I(link['LEGACY_A']['n_lines']):,}줄 · B {I(link['LEGACY_B']['n_lines']):,}줄", 660, 192, 236, P(12.5, MUTED, leading=18))
arrow(612, 338, 636, 338, GOOD)
takeaway("→ 정제 후에는 두 시스템 기록 모두 공통 기준정보와 오류 없이 이어집니다. 통합 전 검증이 먼저입니다.", 50)

# 3.3 결과 종합
slide("3.3 결과 종합")
summ = [["품질", f"시스템 자체 결함 건수 A·B 차이 {max_gap:.0f}% 이내", "어느 쪽이 더 낫다고 말할 수 없음"],
        ["구조", "기준정보(단가표·진료과·코드 사전)는 전부 A, 매핑 36/36 동일", "기준정보는 이미 하나 → 남은 것은 사람·거래 기록"],
        ["구조", f"한 병원 = 한 시스템({chain_same_pct:.0f}%), 환자 {both_pct:.1f}%가 두 시스템 이용", "환자 명단이 나뉘어 있음"],
        ["운영", f"미이행 예약 A {a_cancel_pct:.1f}%(취소) · B {b_noshow_pct:.1f}%(노쇼)", "A는 2시간 전, B는 3시간 뒤 파악 → 시스템 차이로 추정"],
        ["기준정보", f"단가표 {bad_rows}행 오류 → 두 시스템 {lines_all:,}줄", "공통 기준정보 오류가 다른 시스템까지 오염"],
        ["정합성", "정제 후 기준정보 연결 오류 0건", "검증을 거치면 하나로 이어질 수 있음"]]
table_rows(48, 446, [120, 404, 340], ["관점", "분석 결과", "의미"], summ, size=13, row_h=40, aligns=["l", "l", "l"])
takeaway("→ 우열은 없지만, 환자 명단 · 파악 시점 · 기준정보 오염 때문에 최적화를 위해 두 시스템은 통합해야 합니다.", 50)

# ---------------------------------------------------------------- 4. 결론
section_cover("4", "결론", ["4.1 To-Be", "4.2 결론 및 요약 · 한계점 · 보완점"])

# 4.1 To-Be
slide("4.1 To-Be: 장점을 모은 통합 시스템 C")
for i, (t, d, col) in enumerate((("LEGACY_A", f"병원 {hosp['LEGACY_A']}곳<br/>취소를 예약 2시간 전에 파악", A),
                                  ("LEGACY_B", f"병원 {hosp['LEGACY_B']}곳<br/>노쇼를 예약 3시간 뒤에 파악", B))):
    y0 = 300 - i * 150
    box(48, y0, 220, 130, t, d, col, size=14)
arrow(276, 300, 330, 300)
arrow(276, 215, 330, 250)
c.setFillColor(colors.HexColor("#fff7e6"))
c.roundRect(336, 170, 230, 230, 10, stroke=0, fill=1)
c.setFillColor(colors.HexColor("#b38b00"))
c.setFont("MGB", 15)
c.drawString(354, 372, "통합 전 검증 단계")
para("• 실무자 의견으로 A·B 장점 선정<br/>• 표준 사전(코드·용어·단위) 확정<br/>• 공통 기준정보 품질 검사<br/>• 정제(Bronze → Silver) 규칙 적용",
     354, 360, 200, P(13.5, INK, leading=24))
arrow(572, 285, 620, 285, GOOD)
c.setFillColor(colors.HexColor("#eef7f1"))
c.roundRect(626, 130, 286, 320, 10, stroke=0, fill=1)
c.setFillColor(colors.HexColor(GOOD))
c.setFont("MGB", 20)
c.drawString(646, 418, "통합 시스템 C")
items = ["단일 환자 마스터 (환자 ID 한 곳에서 발급)", "검증된 공통 기준정보 (단가표·진료과·코드)", "취소·노쇼 파악 시점 기준을 표준으로 통일",
         "source_system 은 계보 컬럼으로 유지"]
yy = 390
for it in items:
    c.setFillColor(colors.HexColor(GOOD))
    c.circle(652, yy + 4, 4, stroke=0, fill=1)
    para(it, 664, yy + 12, 236, P(13, INK, leading=18))
    yy -= 50
takeaway("→ 두 시스템 중 하나를 고르지 않고, 검증을 거쳐 장점을 모은 새 시스템 C로 통합합니다.", 60)

# 4.2 결론·한계·보완점
slide("4.2 결론 및 요약 · 한계점 · 보완점")
box(48, 110, 280, 340, "결론 및 요약",
    "• 두 시스템은 품질이 같아 우열을 말할 수 없음<br/>• 하지만 환자 명단 분리, 취소·노쇼 파악 시점 차이, 공통 기준정보 오염 때문에 통합이 필요<br/>• A·B 장점을 모은 새 시스템 C로 통합 권고", NAVY, size=15.5)
box(340, 110, 280, 340, "한계점",
    "• A/B 는 명세상 가상의 출처 (실제 제품 평가 아님)<br/>• 한 병원은 한 시스템만 써서 시스템 차이와 병원 차이를 구분할 수 없음<br/>• 20%, 2시간 전처럼 딱 떨어지는 만든 데이터", B, size=15.5)
box(632, 110, 280, 340, "보완점",
    "• 실무자 인터뷰로 두 시스템의 기능 차이 확인<br/>• 같은 병원에서 시스템을 바꾼 기록 등으로 시스템 효과 분리<br/>• 실제 운영 데이터로 재검증<br/>• Gold 테이블 DB 적재와 정기 품질 점검", GOOD, size=15.5)

# 4.3 끝
slide("", dark=True)
para("품질은 같습니다.<br/>하지만 기록은 둘로 나뉘어 있습니다.<br/>그래서 <font color='#ffb48f'>장점을 모은 시스템 C로 통합</font>합니다.", 70, 400, 820, P(34, "#ffffff", True, 50))
c.setFont("MG", 16)
c.setFillColor(colors.HexColor("#d6e2ef"))
c.drawString(70, 120, "감사합니다  ·  질문 받겠습니다")
c.setFont("MG", 11)
c.drawString(70, 90, "데이터: team3_medallion / team3_medallion_dq (조회 전용), 원본 CSV(원본 집계·단가표 오류 파급)")

c.showPage()
c.save()
print("saved", PDF, PAGE[0], "pages")
