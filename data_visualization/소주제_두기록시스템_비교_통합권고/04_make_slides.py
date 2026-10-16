# -*- coding: utf-8 -*-
"""
[황유민] 발표 자료(16:9 슬라이드 PDF, 10장) 생성 - 두 기록 시스템(LEGACY_A/B) 비교와 통합 전 확인 사항.
- 데이터 출처: DB(team3_medallion, team3_medallion_dq) 조회 결과 텍스트. 모두 조회 전용 세션에서 SELECT 만 실행.
    ../분석초안/out/05_source.txt (S01, S03), 06_rank.txt (S15, S16), 07_master.txt (M01~M05), 08_facts.txt (F01~F06)
  단, 원본 단가표 오류의 파급(슬라이드 7 왼쪽)은 DB 에 원본(Bronze)이 없어 원본 CSV 에서 계산한다(화면에 '원본 기준' 표시).
- 출력: out/charts/d_*.png (슬라이드 차트), 발표자료_원천시스템_통합.pdf
실행: python -I 04_make_slides.py <원본 data 폴더>
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
PDF = os.path.join(BASE, "발표자료_원천시스템_통합.pdf")
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
TOTAL = 10


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

# 1. 표지
slide("", dark=True)
c.setFillColor(colors.HexColor("#9fb7d3"))
c.setFont("MGB", 14)
c.drawString(70, 380, "병원 진료 및 수납 시스템 최적화")
para("두 기록 시스템,<br/>하나로 합치기 전에 확인할 것", 70, 360, 820, P(40, "#ffffff", True, 54))
para("LEGACY_A / LEGACY_B 비교와 통합 권고", 70, 228, 820, P(18, "#d6e2ef", leading=26))
c.setFont("MG", 14)
c.setFillColor(colors.HexColor("#d6e2ef"))
c.drawString(70, 90, "황유민  ·  Medallion(Bronze → Silver → Gold) 분석  ·  데이터: team3_medallion DB")

# 2. 오늘의 결론
slide("오늘의 결론", "한 줄 요약")
para("두 시스템은 <b>품질이 같아서</b> 어느 쪽이 더 낫다고 말할 수 없습니다.<br/>"
     "하지만 <b>환자 명단이 나뉘어</b> 있고, <b>취소·노쇼 파악 시점이 다르며</b>, <b>공통 기준정보 오류가 두 시스템에 함께 퍼집니다</b>.<br/>"
     "그래서 두 시스템의 장점을 종합한 <b>새 시스템 C로 통합</b>할 것을 권고합니다.",
     48, 420, 864, P(19, INK, leading=34))
cw = (W - 96 - 60) / 4
card(48, 92, cw, 150, "같다", f"시스템 자체 결함 건수<br/>A·B 차이 {max_gap:.0f}% 이내", A, big_size=26)
card(48 + (cw + 20), 92, cw, 150, f"{both_pct:.1f}%", "두 시스템 병원을<br/>모두 이용한 환자", B, big_size=26)
card(48 + 2 * (cw + 20), 92, cw, 150, "2h 전 · 3h 뒤", "취소(A)·노쇼(B)를<br/>파악하는 시점", NAVY, big_size=24)
card(48 + 3 * (cw + 20), 92, cw, 150, f"{bad_rows}행 → {lines_all / 10000:.1f}만", f"단가표 오류 {bad_rows}행이<br/>두 시스템 진료 서비스<br/>{lines_all / 10000:.1f}만 줄에 영향", NAVY, big_size=24)

# 3. LEGACY_A / B 란?
slide("LEGACY_A / LEGACY_B 는 무엇인가요?", "용어 이해", source="team3_medallion.hospitals, 명세서")
box(48, 320, 864, 120, "한 줄 정의",
    "모든 기록 끝에 붙은 <b>출처 표시</b>입니다. 이 기록이 원래 <b>어느 전산 시스템에 적혀 있었는지</b>를 알려 줍니다.", size=18)
para("<b>우리 데이터에서는</b>", 48, 290, 864, P(16, NAVY, True))
para(f"• 병원 {hosp['LEGACY_A'] + hosp['LEGACY_B']}곳이 <b>A {hosp['LEGACY_A']}곳, B {hosp['LEGACY_B']}곳</b>으로 나뉘어 있습니다.<br/>"
     "• 모든 테이블에 <b>source_system</b> 칸으로 남아 있습니다.<br/>"
     "• 명세서상 <b>실제 제품이 아니라 '합쳐지는 상황'을 연습하기 위한 가상 출처</b>입니다.",
     48, 262, 864, P(16, INK, leading=28))

# 4. 인사이트 1·2
slide("품질은 같고, 기준정보는 이미 하나다", "인사이트 1 · 2", source="team3_medallion_dq.reclean_quarantine, team3_medallion 기준정보 4개 테이블")
image("d_direct_defects.png", 40, 110, 540, 350)
c.setFillColor(colors.HexColor(SOFT))
c.roundRect(600, 110, 312, 350, 10, stroke=0, fill=1)
c.setFillColor(colors.HexColor(NAVY))
c.setFont("MGB", 15)
c.drawString(618, 432, "기준정보는 전부 A 하나")
rows_m = [("서비스 단가표", master["service_catalog"]), ("진료과", master["departments"]), ("코드 사전", master["code_dictionary"])]
yy = 400
for name, d in rows_m:
    c.setFillColor(colors.HexColor(INK))
    c.setFont("MG", 14)
    c.drawString(618, yy, name)
    c.setFont("MGB", 14)
    c.drawRightString(892, yy, f"A {d.get('LEGACY_A', 0)}행 · B {d.get('LEGACY_B', 0)}행")
    yy -= 30
c.setFont("MG", 14)
c.setFillColor(colors.HexColor(INK))
c.drawString(618, yy, "원천 코드 매핑")
c.setFont("MGB", 14)
c.drawRightString(892, yy, f"A·B {same_map['same_in_b']}/{same_map['a_rows']} 동일")
para("나뉘어 있는 것은 병원·의사·환자와 예약·접수·진료·결제 기록뿐입니다.", 618, yy - 24, 276, P(13.5, MUTED, leading=20))
takeaway("→ A/B 중 어느 쪽이 더 낫다고 말할 수 있는 근거는 없습니다.", 50)

# 5. 인사이트 3·4
slide("병원은 나뉘어 있고, 환자는 오간다", "인사이트 3 · 4", source="team3_medallion (hospitals, encounters~hospitals 연결, appointments, checkins, patients)")
card(48, 330, 300, 120, f"{hosp['LEGACY_A']} : {hosp['LEGACY_B']}", "A 병원 : B 병원", NAVY, big_size=30)
card(48, 192, 300, 124, f"{chain_same_pct:.0f}%", f"진료 {chain_total:,}건 중 병원·구간·접수·진료가<br/>같은 시스템인 비율 (한 병원 = 한 시스템)", NAVY, big_size=30)
para("그래서 A/B 비교는 곧 <b>병원군 비교</b>입니다. 차이가 시스템 때문인지 병원 특성 때문인지는 구분할 수 없습니다.",
     48, 176, 300, P(12.5, MUTED, leading=18))
image("d_patient_cross.png", 362, 150, 550, 300)
para(f"예약한 환자의 <b>{both_pct:.1f}%</b>가 A·B 병원을 모두 이용 · 접수의 <b>{ck_cross_pct:.1f}%</b>는 다른 시스템에 등록된 환자",
     380, 146, 530, P(13, INK, leading=18))
takeaway("→ 병원은 시스템별로 나뉘어 있지만 환자는 그렇지 않습니다. 환자 명단부터 하나로 합쳐야 합니다.", 50)

# 6. 인사이트 5
slide("같은 20%, 병원이 아는 시점이 다르다", "인사이트 5", source="team3_medallion.appointments, appointment_events")
cw2 = (W - 96 - 20) / 2
card(48, 342, cw2, 108, f"A {a_cancel_pct:.1f}%  ·  B {b_noshow_pct:.1f}%", "지켜지지 않은 예약 비율 (A는 전부 '취소', B는 전부 '노쇼')", NAVY, big_size=26)
card(48 + cw2 + 20, 342, cw2, 108, "2시간 전  vs  3시간 뒤", "그 사실이 기록된 시점 (예약 시각 기준)", B, big_size=26)
image("d_unmet_timing.png", 48, 116, 864, 218)
takeaway("→ A 시스템은 모든 취소를 예약 2시간 전에, B 시스템은 모든 노쇼를 예약 3시간 뒤에 파악합니다. "
         "병원 차이인지 시스템 차이인지 확정할 수는 없지만, 그 비율이 100%인 것으로 보아 시스템 차이로 추정됩니다.", 44, 64)

# 7. 인사이트 7 + 정제 결과
slide("공통 기준정보의 작은 오류가 두 시스템에 퍼진다", "인사이트 7 · 정제로 해결", source="왼쪽: 제공 데이터 원본 / 오른쪽: team3_medallion (service_catalog, encounter_services, departments)")
# 왼쪽 흐름
box(48, 270, 250, 136, "A 단가표", f"{scb.height}행 중 <b>{bad_rows}행 오류</b><br/>(음수 단가 {len(neg_keys)}행, ID 표기 오류 {len(hyp_keys)}행)", A, size=14)
arrow(304, 338, 352, 338)
box(358, 270, 250, 136, "두 시스템의 진료 서비스", f"<b>{lines_all:,}줄</b>이 오류 행을 참조<br/>A {lines_a:,}줄 · B {lines_b:,}줄", B, size=14)
para(f"단가표 1행 오류가 평균 약 {lines_all / bad_rows / 10000:.1f}만 줄에 영향 → 이 행을 격리하면 두 시스템 기록이 함께 끊깁니다.",
     48, 258, 560, P(13.5, MUTED, leading=20))
# 오른쪽 결과
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

# 8. 통합 권고
slide("통합 권고")


def rec_row(y_top, h, n, color, title, body_html):
    c.setFillColor(colors.HexColor(SOFT))
    c.roundRect(48, y_top - h, 864, h, 10, stroke=0, fill=1)
    c.setFillColor(colors.HexColor(color))
    c.circle(86, y_top - 34, 19, stroke=0, fill=1)
    c.setFillColor(colors.HexColor("#ffffff"))
    c.setFont("MGB", 18)
    c.drawCentredString(86, y_top - 40, n)
    c.setFillColor(colors.HexColor(INK))
    c.setFont("MGB", 18)
    c.drawString(122, y_top - 40, title)
    if body_html:
        para(body_html, 122, y_top - 54, 770, P(14, MUTED, leading=22))


rec_row(446, 74, "1", A, "두 시스템 중 어느 쪽이 더 좋다고 말할 수는 없다",
        f"시스템 자체 결함 건수가 A·B 거의 같음 (차이 {max_gap:.0f}% 이내)")
rec_row(360, 126, "2", B, "하지만 두 시스템은 통합해야 한다",
        f"• <b>환자 명단이 나뉘어 있음</b>: 환자의 {both_pct:.1f}%가 A·B 병원을 모두 이용<br/>"
        f"• <b>취소·노쇼 파악 시점이 다름</b>: A는 예약 2시간 전, B는 예약 3시간 뒤에 파악<br/>"
        f"• <b>공통 기준정보 오류가 다른 시스템까지 오염</b>: 단가표 {bad_rows}행 오류가 두 시스템 진료 서비스 {lines_all:,}줄에 영향")
rec_row(220, 100, "3", NAVY, "A·B의 장점을 종합한 새 시스템 C로 통합할 것을 권고한다",
        "실무자 의견을 바탕으로 두 시스템의 장점을 모아 새로운 통합 시스템 C를 만들고, 환자 명단과 기준정보를 하나로 관리한다")


# 9. 한계
slide("한계 (꼭 함께 말할 것)", "정리")
box(48, 110, 864, 340, "이 분석으로 말할 수 없는 것",
    "• A/B 는 명세상 <b>가상의 출처</b>입니다. 실제 제품을 평가한 것이 아닙니다.<br/>"
    "• 한 병원은 한 시스템만 씁니다. 그래서 차이가 <b>시스템 때문인지 병원 특성 때문인지 구분할 수 없습니다.</b><br/>"
    "• 20%, 2시간 전처럼 <b>딱 떨어지는 만든 데이터</b>입니다. 현실 병원에 그대로 적용된다고 말할 수 없습니다.<br/>"
    "• 그래서 이 분석의 가치는 '어느 시스템이 좋다'가 아니라 <b>통합 전에 무엇을 먼저 확인해야 하는지</b> 보여 준 데 있습니다.<br/>"
    "• 숫자는 정제된 DB(team3_medallion) 기준이며, 원본 단가표 오류의 파급만 원본 CSV 기준입니다.", B, size=18)

# 10. 마무리
slide("", dark=True)
para("품질은 같습니다.<br/>하지만 기록은 둘로 나뉘어 있습니다.<br/>그래서 <font color='#ffb48f'>장점을 모은 시스템 C로 통합</font>합니다.",
     70, 400, 820, P(34, "#ffffff", True, 50))
c.setFont("MG", 16)
c.setFillColor(colors.HexColor("#d6e2ef"))
c.drawString(70, 120, "감사합니다  ·  질문 받겠습니다")
c.setFont("MG", 11)
c.drawString(70, 90, "데이터: team3_medallion / team3_medallion_dq (조회 전용), 원본 CSV(단가표 오류 파급만)")

c.showPage()
c.save()
print("saved", PDF, PAGE[0], "pages")
