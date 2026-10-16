import duckdb, os, numpy as np, pandas as pd, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager as fm
fm.fontManager.addfont(r"C:\Windows\Fonts\malgun.ttf"); fm.fontManager.addfont(r"C:\Windows\Fonts\malgunbd.ttf")
plt.rcParams.update({"font.family": "Malgun Gothic", "axes.unicode_minus": False, "axes.spines.top": False,
                     "axes.spines.right": False, "font.size": 13, "figure.dpi": 150})
NAVY, TEAL, ORANGE, RED, GRAY = "#1F3A5F", "#2A9D8F", "#F4A261", "#E76F51", "#B0B7C3"
O = "pivot/out/"; C = "pivot/charts/"; os.makedirs(O, exist_ok=True); os.makedirs(C, exist_ok=True)
for f in os.listdir(C): os.remove(C + f)
con = duckdb.connect("pivot/work/hospital.duckdb", read_only=True)
for t in [r[0] for r in con.execute("select table_name from information_schema.tables where table_name like 'g%'").fetchall()]:
    con.execute(f"select * from {t}").df().to_csv(O + t + ".csv", index=False, encoding="utf-8-sig")
q = lambda s: con.sql(s).df()
def save(fig, name): fig.tight_layout(); fig.savefig(C + name, bbox_inches="tight"); plt.close(fig)

# 1. 퍼널 + 보류
h = q("select * from g1b_hold").set_index("item").n; f = q("select * from g1_funnel").set_index("segment")
tot = int(h.sum()); fig, axes = plt.subplots(1, 2, figsize=(13.5, 5), gridspec_kw={"width_ratios": [1.15, 1]})
ax = axes[0]; segs = [("비교 가능", h["비교 가능"], TEAL), ("H1 공식 Silver\n미통과 진료", h.iloc[0], GRAY), ("H2 정상 접수\n연결 불가", h.iloc[1], ORANGE), ("H3 결제 일부\n격리", h.iloc[2], RED)][::-1]
ax.barh([s_[0] for s_ in segs], [s_[1] / 1000 for s_ in segs], color=[s_[2] for s_ in segs], height=.62)
for i_, s_ in enumerate(segs): ax.text(s_[1] / 1000 + 8, i_, f"{int(s_[1]):,}건 ({s_[1]/tot*100:.1f}%)", va="center", fontsize=11.5)
ax.set_xlim(0, 860); ax.set_xlabel("진료 건수 (천 건)"); ax.set_title("진료 100만 건 중 대사 가능 범위", loc="left", fontweight="bold")
ax = axes[1]; st = ["① 비교 가능 진료", "② 결제 기록 발생", "③ 청구액=순수납"]; x = np.arange(3); w = .38
for i, (seg, col, lab) in enumerate([("RESERVED", NAVY, "예약 진료"), ("WALK_IN", TEAL, "현장접수 진료")]):
    v = f.loc[seg, ["n_valid", "n_has_payment", "n_match"]].values.astype(float)
    ax.bar(x + (i - .5) * w, v / 1000, w, color=col, label=lab)
    for xi, vi in zip(x + (i - .5) * w, v): ax.text(xi, vi / 1000 + 8, f"{vi/1000:,.0f}천\n100%", ha="center", fontsize=10)
ax.set_xticks(x); ax.set_xticklabels(st, fontsize=11); ax.set_ylim(0, 760); ax.set_ylabel("진료 건수 (천 건)"); ax.legend(frameon=False, loc="upper center", ncol=2)
ax.set_title("비교 가능 진료의 퍼널: 단계별 100% 통과", loc="left", fontweight="bold")
save(fig, "01_funnel.png")

# 2. 코호트
c = q("select * from g2_cohort"); c["visit_month"] = pd.to_datetime(c.visit_month); hm = q("select * from g2b_hold_month"); hm["visit_month"] = pd.to_datetime(hm.visit_month)
fig, axes = plt.subplots(1, 2, figsize=(13.5, 4.8))
for seg, col, lab in [("RESERVED", NAVY, "예약 진료"), ("WALK_IN", TEAL, "현장접수 진료")]:
    s = c[c.visit_type == seg]; axes[0].plot(s.visit_month, s.match_rate * 100, "o-", color=col, label=lab, ms=3.5, lw=2)
axes[0].set_ylim(90, 101); axes[0].set_ylabel("청구액=순수납 일치율 (%)"); axes[0].legend(frameon=False, loc="lower right")
axes[0].set_title("월별 일치율 (36개월 모두 100%)", loc="left", fontweight="bold", fontsize=12.5)
r = c[c.visit_type == "RESERVED"].sort_values("visit_month")
axes[1].plot(r.visit_month, r.split_rate * 100, "s-", color=NAVY, label="분할결제율", ms=3.5, lw=2)
axes[1].plot(r.visit_month, r.refund_rate * 100, "o-", color=ORANGE, label="환불 승인율", ms=3.5, lw=2)
axes[1].plot(hm.visit_month, hm.hold_rate * 100, "^-", color=RED, label="보류율 (공식 Silver 통과 진료 기준)", ms=3.5, lw=1.6)
axes[1].set_ylim(0, 60); axes[1].set_ylabel("%"); axes[1].legend(frameon=False, loc="center right")
import matplotlib.dates as mdates
for a_ in axes: a_.xaxis.set_major_locator(mdates.YearLocator()); a_.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
axes[1].set_title("예약 진료의 분할·환불 비율도 월과 무관", loc="left", fontweight="bold", fontsize=12.5)
save(fig, "02_cohort.png")

# 3. 균등성(차원별 범위)
d = q("select dim, grp, n, n_hold, n_refund, n_split from g4_dim"); nm = {"hospital_region": "병원 지역(18)", "department": "진료과(13)", "visit_month": "진료 월(36)", "hospital_type": "병원 종별(4)",
    "visit_dow": "요일(5)", "source_system": "청구 시스템(2)", "visit_year": "진료 연도(3)", "visit_hour": "시간대(8)", "visit_type": "접수 유형(2)"}
order = ["hospital_region", "department", "visit_month", "hospital_type", "visit_dow", "source_system", "visit_year", "visit_hour", "visit_type"]
fig, axes = plt.subplots(1, 3, figsize=(14, 5.2), sharey=True)
for ax, (col, ttl, cc) in zip(axes, [("n_hold", "보류율 (%)", GRAY), ("n_refund", "환불 승인율 (%)", ORANGE), ("n_split", "분할결제율 (%)", NAVY)]):
    for i, dim in enumerate(order[::-1]):
        g = d[d.dim == dim]; rate = g[col] / g.n * 100; diff = rate.max() - rate.min(); colr = TEAL if diff > 2 else cc
        ax.plot([rate.min(), rate.max()], [i, i], "-", color=colr, lw=6, solid_capstyle="round"); ax.plot(rate, [i] * len(rate), "|", color="black", ms=9)
    ax.set_yticks(range(len(order))); ax.set_yticklabels([nm[k] for k in order[::-1]]); ax.set_title(ttl, loc="left", fontweight="bold"); ax.grid(axis="x", alpha=.25)
axes[0].set_xlim(-.2, 2.2); axes[1].set_xlim(-1, 15); axes[2].set_xlim(-2, 100)
save(fig, "03_uniformity.png")

# 4. 격리 규칙
qr = q("select * from g3_quarantine_rules"); lab = {"FK_MISSING:encounter_id": "진료 FK 부재\n(고아 참조)", "NULL_OR_TYPE:encounter_id": "진료 ID 결측", "AMOUNT_RANGE": "금액 범위 위반\n(≤0)",
    "UNREGISTERED:payment_method": "미등록 결제수단", "NULL_OR_TYPE:transacted_at": "거래일시 결측·형식오류", "UNREGISTERED:transaction_type": "미등록 거래유형",
    "ORIGINAL_UNUSABLE_OR_NOT_PAYMENT": "환불의 원결제\n사용 불가", "ORIGINAL_MISSING": "환불의 원결제\n부재"}
qr["lab"] = qr.rule.map(lab); qr = qr.iloc[::-1]
fig, ax = plt.subplots(figsize=(11.5, 5.6)); ax.barh(qr.lab, qr.n, color=[RED if "금액" in l or "원결제" in l else NAVY for l in qr.lab])
for i, v in enumerate(qr.n): ax.text(v + 250, i, f"{v:,}", va="center")
ax.set_xlim(0, 25500); ax.set_xlabel("영향 거래 수 (한 거래가 여러 규칙에 걸릴 수 있음)"); ax.set_title("격리 결제 88,006건: 정제 규칙별 영향", loc="left", fontweight="bold")
save(fig, "04_quarantine.png")

# 5. 패턴별 업무 점유
p = q("select * from g6_pattern"); p["enc_share"] = p.n / p.n.sum() * 100; p["tx_share"] = p.n_tx / p.n_tx.sum() * 100
ordp = ["현장접수-단일결제", "예약-단일결제", "예약-분할결제", "예약-환불"]; p = p.set_index("pattern").loc[ordp].reset_index()
fig, axes = plt.subplots(1, 2, figsize=(13.5, 4.8), gridspec_kw={"width_ratios": [1.4, 1]}); x = np.arange(4); w = .38
axes[0].bar(x - w / 2, p.enc_share, w, color=GRAY, label="진료 건수 비중"); axes[0].bar(x + w / 2, p.tx_share, w, color=NAVY, label="거래 건수 비중")
for xi, a_, b_ in zip(x, p.enc_share, p.tx_share): axes[0].text(xi - w / 2, a_ + .6, f"{a_:.1f}%", ha="center", fontsize=10.5); axes[0].text(xi + w / 2, b_ + .6, f"{b_:.1f}%", ha="center", fontsize=10.5)
axes[0].set_xticks(x); axes[0].set_xticklabels([s.replace("-", "\n") for s in p.pattern]); axes[0].set_ylim(0, 62); axes[0].legend(frameon=False); axes[0].set_ylabel("%")
axes[0].set_title("수납 패턴별 진료 비중 vs 거래 비중", loc="left", fontweight="bold")
axes[1].bar(x, p.tx_per_enc, color=[TEAL, GRAY, NAVY, ORANGE]); [axes[1].text(i, v + .03, f"{v:.1f}건", ha="center") for i, v in enumerate(p.tx_per_enc)]
axes[1].set_xticks(x); axes[1].set_xticklabels([s.replace("-", "\n") for s in p.pattern], fontsize=11); axes[1].set_ylim(0, 2.5); axes[1].set_title("진료 1건당 거래 건수", loc="left", fontweight="bold")
save(fig, "05_pattern.png")

# 6. 시간대
hr = q("select * from g5_hour"); hx = hr.visit_hour.astype(str) + "시"; fig, axes = plt.subplots(1, 2, figsize=(13.5, 4.7))
axes[0].bar(hx, hr.n / 1000, color="#DDE3EC"); axes[0].set_ylabel("진료 건수 (천 건)"); a2 = axes[0].twinx(); a2.spines["right"].set_visible(True)
a2.plot(hx, hr.split_share * 100, "s-", color=NAVY, lw=2.5); a2.set_ylim(0, 108); a2.set_ylabel("분할결제 비율 (%)", color=NAVY)
axes[0].set_title("시간대별 진료량(막대)과 분할결제 비율(선)", loc="left", fontweight="bold", fontsize=12.5)
axes[1].bar(hx, hr.tx_per_enc, color=[RED if v > 1.9 else GRAY for v in hr.tx_per_enc]); [axes[1].text(i, v + .02, f"{v:.2f}", ha="center", fontsize=10.5) for i, v in enumerate(hr.tx_per_enc)]
axes[1].set_ylim(0, 2.4); axes[1].set_title("진료 1건당 거래 건수 (수납 업무 부담 대용)", loc="left", fontweight="bold", fontsize=12.5)
save(fig, "06_hour.png")

# 7. 청구 시스템
sp = q("select * from g7_system_price"); y = q("select * from g7b_system_year"); fig, axes = plt.subplots(1, 2, figsize=(13, 4.6))
for sy, col in [("LEGACY_A", NAVY), ("LEGACY_B", ORANGE)]:
    dd = y[y.source_system == sy]; axes[0].plot(dd.yr, dd.avg_gross / 1000, "o-", color=col, lw=2.5, label=sy)
    for xx, vv in zip(dd.yr, dd.avg_gross / 1000): axes[0].text(xx, vv + .8, f"{vv:.1f}", ha="center", fontsize=10.5)
axes[0].set_xticks([2023, 2024, 2025]); axes[0].set_ylim(28, 50); axes[0].legend(frameon=False, loc="upper left"); axes[0].set_title("진료당 평균 청구액 (천 원)", loc="left", fontweight="bold")
axes[1].bar(sp.source_system, sp.avg_qty, color=[NAVY, ORANGE], width=.5); [axes[1].text(i, v + .03, f"{v:.2f}", ha="center") for i, v in enumerate(sp.avg_qty)]
du = (sp.avg_unit.iloc[1] / sp.avg_unit.iloc[0] - 1) * 100; axes[1].set_ylim(0, 2.1); axes[1].set_title(f"항목당 평균 수량 (평균 단가 차이 {du:.1f}%)", loc="left", fontweight="bold")
save(fig, "07_system.png")
print(os.listdir(C))


