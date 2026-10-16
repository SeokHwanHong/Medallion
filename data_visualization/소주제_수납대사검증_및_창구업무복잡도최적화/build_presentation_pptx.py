# -*- coding: utf-8 -*-
"""
Team 3 통일 디자인 시스템 기반 PPTX & PDF 생성기
- 첨부된 12장 PDF 레퍼런스('외래 환자는 왜 떠났고, 의료 자원은 어디로 가야 하는가')와 100% 동일한 레이아웃/컬러/타이포그래피 적용
- 향후 4대 관점(①예약, ②접수, ③진료, ④수납) 통합 PPT 제작 시 그대로 확장 가능한 모듈형 템플릿 구조
"""
import os
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE
from pptx.dml.color import RGBColor

# ==============================================================================
# 1. 컬러 팔레트 (PDF 레퍼런스 100% 동일 추출)
# ==============================================================================
DARK_BG       = RGBColor(10, 19, 28)     # #0A131C (표지, 11p, 12p 다크 네이비 배경)
DARK_CARD     = RGBColor(17, 31, 44)     # #111F2C (다크 슬라이드 내부 카드 배경)
DARK_BORDER   = RGBColor(32, 65, 88)     # #204158 (다크 슬라이드 카드 테두리)
DARK_PILL_BG  = RGBColor(15, 43, 60)     # #0F2B3C (다크 슬라이드 상단 배지 배경)

LIGHT_BG      = RGBColor(248, 250, 252)  # #F8FAFC (본문 슬라이드 밝은 배경)
WHITE         = RGBColor(255, 255, 255)  # #FFFFFF (화이트 카드 배경)
CARD_BORDER   = RGBColor(226, 232, 240)  # #E2E8F0 (화이트 카드 테두리)
LIGHT_PILL_BG = RGBColor(224, 242, 254)  # #E0F2FE (본문 상단 하늘색 배지 배경)
LIGHT_PILL_FG = RGBColor(2, 132, 199)    # #0284C7 (본문 상단 배지 텍스트)

INK_DARK      = RGBColor(15, 23, 42)     # #0F172A (본문 메인 타이틀 & 표 헤더)
INK_BODY      = RGBColor(51, 65, 85)     # #334155 (본문 일반 텍스트)
INK_MUTED     = RGBColor(100, 116, 139)  # #64748B (서브타이틀, 푸터)
DARK_SUB      = RGBColor(148, 163, 184)  # #94A3B8 (다크 슬라이드 보조 텍스트)

TEAL_BRIGHT   = RGBColor(45, 212, 191)   # #2DD4BF (다크 슬라이드 민트/틸 포인트)
TEAL_ACCENT   = RGBColor(16, 185, 129)   # #10B981 (본문 그린/틸 포인트)
BLUE_ACCENT   = RGBColor(14, 165, 233)   # #0EA5E9 (본문 블루 포인트)
PURPLE_ACCENT = RGBColor(99, 102, 241)   # #6366F1 (관점 1 퍼플 포인트)
RED_ACCENT    = RGBColor(239, 68, 68)    # #EF4444 (경고/병목 레드 포인트)
RED_SOFT_BG   = RGBColor(254, 242, 242)  # #FEF2F2 (퍼널 경고 카드 연분홍 배경)
RED_SOFT_BD   = RGBColor(252, 165, 165)  # #FCA5A5 (퍼널 경고 카드 테두리)
ROW_ALT       = RGBColor(241, 245, 249)  # #F1F5F9 (표 구분선/연회색)

FONT = "맑은 고딕"

prs = Presentation()
prs.slide_width = Inches(13.333)
prs.slide_height = Inches(7.5)
BLANK = prs.slide_layouts[6]

# ==============================================================================
# 2. 공통 컴포넌트 헬퍼 함수 (4명 통합 PPT에서도 그대로 재사용 가능)
# ==============================================================================
def set_bg(slide, color):
    bg = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, Inches(13.333), Inches(7.5))
    bg.fill.solid()
    bg.fill.fore_color.rgb = color
    bg.line.fill.background()
    return bg

def add_text(slide, x, y, w, h, lines, size=11, color=INK_BODY, bold=False, align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.TOP, line_spacing=1.25):
    tb = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = tb.text_frame
    tf.word_wrap = True
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    tf.vertical_anchor = anchor
    if isinstance(lines, str):
        lines = [lines]
    for i, item in enumerate(lines):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = align
        p.line_spacing = line_spacing
        if isinstance(item, tuple):
            txt, st = item
            p.space_after = Pt(st.get("space_after", 4))
            r = p.add_run()
            r.text = txt
            r.font.name = FONT
            r.font.size = Pt(st.get("size", size))
            r.font.bold = st.get("bold", bold)
            r.font.color.rgb = st.get("color", color)
        elif isinstance(item, list):
            # 한 문단 내 여러 스타일 조합 [(텍스트, 스타일dict), ...]
            p.space_after = Pt(4)
            for sub_txt, sub_st in item:
                r = p.add_run()
                r.text = sub_txt
                r.font.name = FONT
                r.font.size = Pt(sub_st.get("size", size))
                r.font.bold = sub_st.get("bold", bold)
                r.font.color.rgb = sub_st.get("color", color)
        else:
            p.space_after = Pt(4)
            r = p.add_run()
            r.text = str(item)
            r.font.name = FONT
            r.font.size = Pt(size)
            r.font.bold = bold
            r.font.color.rgb = color
    return tb

def add_card(slide, x, y, w, h, fill=WHITE, border=CARD_BORDER, rounded=True, adj=0.03):
    shape_type = MSO_SHAPE.ROUNDED_RECTANGLE if rounded else MSO_SHAPE.RECTANGLE
    s = slide.shapes.add_shape(shape_type, Inches(x), Inches(y), Inches(w), Inches(h))
    if rounded and s.adjustments:
        s.adjustments[0] = adj
    s.fill.solid()
    s.fill.fore_color.rgb = fill
    if border:
        s.line.color.rgb = border
        s.line.width = Pt(1)
    else:
        s.line.fill.background()
    return s

def add_left_accent_card(slide, x, y, w, h, accent_color, fill=WHITE, border=CARD_BORDER):
    """PDF 특유의 좌측 굵은 컬러 보더가 들어간 콜아웃 카드"""
    card = add_card(slide, x, y, w, h, fill=fill, border=border, rounded=True, adj=0.02)
    bar = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(x), Inches(y), Inches(0.08), Inches(h))
    if bar.adjustments:
        bar.adjustments[0] = 0.2
    bar.fill.solid()
    bar.fill.fore_color.rgb = accent_color
    bar.line.fill.background()
    return card

def add_top_accent_card(slide, x, y, w, h, accent_color, fill=WHITE, border=CARD_BORDER):
    """PDF Slide 02 특유의 상단 굵은 컬러 바가 들어간 4대 관점 카드"""
    card = add_card(slide, x, y, w, h, fill=fill, border=border, rounded=True, adj=0.03)
    bar = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(x), Inches(y), Inches(w), Inches(0.08))
    if bar.adjustments:
        bar.adjustments[0] = 0.2
    bar.fill.solid()
    bar.fill.fore_color.rgb = accent_color
    bar.line.fill.background()
    return card

def add_footer(slide, left_label, slide_num_str, dark=False):
    line_col = RGBColor(30, 41, 59) if dark else CARD_BORDER
    txt_col = RGBColor(100, 116, 139) if dark else INK_MUTED
    line = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0.8), Inches(6.75), Inches(11.733), Inches(0.015))
    line.fill.solid()
    line.fill.fore_color.rgb = line_col
    line.line.fill.background()
    add_text(slide, 0.8, 6.85, 8.8, 0.3, left_label, size=9.5, color=txt_col)
    add_text(slide, 9.7, 6.85, 2.833, 0.3, slide_num_str, size=9.5, color=txt_col, align=PP_ALIGN.RIGHT)

def create_light_slide(badge_text, title_text, subtitle_text, footer_left, slide_num):
    s = prs.slides.add_slide(BLANK)
    set_bg(s, LIGHT_BG)
    # 상단 배지 (Pill)
    pill_w = max(1.5, len(badge_text) * 0.11 + 0.35)
    pill = add_card(s, 0.8, 0.62, pill_w, 0.28, fill=LIGHT_PILL_BG, border=None, rounded=True, adj=0.5)
    add_text(s, 0.8, 0.62, pill_w, 0.28, badge_text, size=8.5, color=LIGHT_PILL_FG, bold=True, align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)
    # 메인 타이틀 & 서브타이틀
    add_text(s, 0.8, 0.98, 11.7, 0.45, title_text, size=22, color=INK_DARK, bold=True)
    add_text(s, 0.8, 1.44, 11.7, 0.3, subtitle_text, size=11.5, color=INK_MUTED)
    add_footer(s, footer_left, f"Slide {slide_num:02d}", dark=False)
    return s

def create_dark_slide(badge_text, title_text, footer_left, slide_num):
    s = prs.slides.add_slide(BLANK)
    set_bg(s, DARK_BG)
    pill_w = max(1.8, len(badge_text) * 0.115 + 0.4)
    add_card(s, 0.8, 0.62, pill_w, 0.28, fill=DARK_PILL_BG, border=DARK_BORDER, rounded=True, adj=0.5)
    add_text(s, 0.8, 0.62, pill_w, 0.28, badge_text, size=8.5, color=TEAL_BRIGHT, bold=True, align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)
    if title_text:
        add_text(s, 0.8, 1.02, 11.7, 0.5, title_text, size=23, color=WHITE, bold=True)
    add_footer(s, footer_left, slide_num if isinstance(slide_num, str) else f"Slide {slide_num:02d}", dark=True)
    return s

def add_clean_table(slide, x, y, w, rows, col_widths, row_h=0.42, font_size=10, highlight_col=None, highlight_color=TEAL_ACCENT):
    """PDF 특유의 다크 네이비 헤더 + 깔끔한 화이트 행 테이블"""
    n_rows = len(rows)
    n_cols = len(rows[0])
    t_shape = slide.shapes.add_table(n_rows, n_cols, Inches(x), Inches(y), Inches(w), Inches(row_h * n_rows))
    tbl = t_shape.table
    for c_idx, cw in enumerate(col_widths):
        tbl.columns[c_idx].width = Inches(cw)
    for r_idx, row in enumerate(rows):
        tbl.rows[r_idx].height = Inches(row_h)
        for c_idx, val in enumerate(row):
            cell = tbl.cell(r_idx, c_idx)
            cell.vertical_anchor = MSO_ANCHOR.MIDDLE
            cell.margin_left = Inches(0.14)
            cell.margin_right = Inches(0.10)
            cell.fill.solid()
            if r_idx == 0:
                cell.fill.fore_color.rgb = INK_DARK
            else:
                cell.fill.fore_color.rgb = WHITE if r_idx % 2 == 1 else ROW_ALT
            p = cell.text_frame.paragraphs[0]
            p.alignment = PP_ALIGN.LEFT
            run = p.add_run()
            run.text = str(val)
            run.font.name = FONT
            run.font.size = Pt(font_size if r_idx > 0 else font_size)
            if r_idx == 0:
                run.font.bold = True
                run.font.color.rgb = WHITE
            elif highlight_col is not None and c_idx == highlight_col:
                run.font.bold = True
                run.font.color.rgb = highlight_color
            elif c_idx == 0:
                run.font.bold = True
                run.font.color.rgb = INK_DARK
            else:
                run.font.bold = False
                run.font.color.rgb = INK_BODY
    return t_shape


# ==============================================================================
# SLIDE 01: 표지 (Dark Navy Theme)
# ==============================================================================
s1 = prs.slides.add_slide(BLANK)
set_bg(s1, DARK_BG)

# 우측 상단 은은한 원형 장식 (PDF 표지 글로우 효과 재현)
glow = s1.shapes.add_shape(MSO_SHAPE.OVAL, Inches(8.8), Inches(-0.8), Inches(4.5), Inches(4.5))
glow.fill.solid()
glow.fill.fore_color.rgb = RGBColor(14, 34, 49)
glow.line.fill.background()

# 상단 배지
add_card(s1, 0.8, 0.62, 4.05, 0.28, fill=DARK_PILL_BG, border=DARK_BORDER, rounded=True, adj=0.5)
add_text(s1, 0.8, 0.62, 4.05, 0.28, "HEALTHCARE DATA ENGINEERING · MEDALLION ARCHITECTURE", size=8.5, color=TEAL_BRIGHT, bold=True, align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)

# 메인 타이틀 2줄 + 구분선
add_text(s1, 0.8, 1.15, 10.5, 0.65, "청구와 수납은 일치했는데 ,", size=34, color=WHITE, bold=True)
t_line = s1.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0.8), Inches(1.88), Inches(6.4), Inches(0.02))
t_line.fill.solid()
t_line.fill.fore_color.rgb = TEAL_BRIGHT
t_line.line.fill.background()
add_text(s1, 0.8, 1.92, 10.5, 0.65, "원무 수납 창구는 왜 과부하에 빠졌는가", size=34, color=TEAL_BRIGHT, bold=True)

# 서브타이틀
add_text(s1, 0.8, 2.75, 8.2, 0.6,
         "1,152만 건 EMR 원시 데이터의 연쇄 격리(38.4%) 정제부터, 23.5만 건 복수 거래 통합 대사 대시보드 및 조건부 재확인 시뮬레이션까지",
         size=12.5, color=DARK_SUB)

# 좌측 하단 메타데이터
add_text(s1, 0.8, 4.75, 6.5, 0.6, [
    ("분석팀: Team 3 (엔지니어링 & 비즈니스 최적화 — 수납·재무 파트)", {"size": 10, "color": INK_MUTED}),
    ("데이터 기준: 전국 485개 병원 정제 DB (완료 진료 496,863건 재정 대사 일치율 100.0% 검증 완료)", {"size": 10, "color": INK_MUTED})
])

# 우측 하단 KPI 박스
add_card(s1, 8.95, 4.28, 3.55, 1.05, fill=DARK_CARD, border=DARK_BORDER, rounded=True, adj=0.12)
add_text(s1, 9.15, 4.40, 3.15, 0.48, "193.8 억 원", size=28, color=TEAL_BRIGHT, bold=True, align=PP_ALIGN.RIGHT)
add_text(s1, 9.05, 4.92, 3.25, 0.3, "외래 완료 진료 순수납액 (청구-수납 대사 100.0%)", size=9.2, color=DARK_SUB, align=PP_ALIGN.RIGHT)

add_footer(s1, "팀 3 · 최종 프로젝트 발표자료 (수납·재무 파트)", "Slide 01", dark=True)


# ==============================================================================
# SLIDE 02: 1. 개요 — 수납·재무 파트 문제 제기 및 4단계 분석 프레임워크
# ==============================================================================
s2 = create_light_slide(
    "1. OVERVIEW",
    "1. 개요 — 수납·재정 대사 문제 제기 및 4단계 분석 프레임워크",
    "원천 데이터 연쇄 격리(정제) ➔ 재정 대사(검증) ➔ 복수 거래·피크타임 병목(원인) ➔ 대시보드·조건부 재확인(해결)까지 전주기를 분석했습니다.",
    "팀 3 · 1. 개요 (수납·재정 대사 및 창구 복잡도 분석 프레임워크)", 2
)

# 상단 대주제 콜아웃 박스
add_left_accent_card(s2, 0.8, 1.9, 11.733, 1.45, RED_ACCENT)
add_text(s2, 1.05, 2.02, 11.2, 1.2, [
    ("📌 분석 주제 (문제 제기) — “청구-수납 차액은 0원인데, 왜 원무 수납 창구는 피크타임마다 마비되는가?”", {"size": 12.5, "bold": True, "color": LIGHT_PILL_FG}),
    ("“진료 단위 통합 대사 대시보드(UI) 및 조건부 재확인(Rule) 도입을 통한 원무 수납 창구 업무 복잡도 최적화”", {"size": 11.5, "bold": True, "color": INK_DARK}),
    ("정제 완료된 진료 496,863건의 최종 재정 대사는 차액 0원(100% 일치)이지만, 전체 진료의 47.4%(23.5만 건)에 달하는 분할결제·환불 복수 거래가 오전 피크 시간대(08~14시)에 몰리면서 창구 직원의 수기 합산 대조와 반복 재확인(+124.1% 작업시간 폭증) 병목을 초래하고 있습니다.", {"size": 10.0, "color": INK_BODY})
])

# 하단 4단계 핵심 분석 카드 (수납·재정 대사 단독 구성)
cards_s2 = [
    ("STEP ① 데이터 정제 (Data Cleaning)", PURPLE_ACCENT, "2단계 연쇄 격리 (38.4%)", "원천 1,152만 건 중 부모키 결함 도미노 격리(reclean_quarantine) 및 무손실 보존", False),
    ("STEP ② 재정 대사 (Reconciliation)", TEAL_ACCENT, "49.7만 건 차액 0원 입증", "순청구액 = 순수납액(193.8억 원) 100.0% 일치 및 환불 원결제 한도 검증", False),
    ("STEP ③ 병목 규명 (Peak & Split)", RED_ACCENT, "복수 거래 47.4% & 피크 집중", "08시 분할(60.5%) · 09~13시 물량(83.5%) · 14시 환불(16.3%) 창구 부하 집중", False),
    ("STEP ④ 개선 효과 (Simulation)", BLUE_ACCENT, "대시보드 & 조건부 재확인", "전수 재확인 시 +124.1% 폭증 ➔ 조건부 축소로 7,757분(21.5인일) 즉시 절감", True)
]
cx = 0.8
for badge_c, col_c, title_c, desc_c, is_active in cards_s2:
    fill_c = RGBColor(240, 249, 255) if is_active else WHITE
    bd_c = BLUE_ACCENT if is_active else CARD_BORDER
    add_top_accent_card(s2, cx, 3.6, 2.75, 1.55, col_c, fill=fill_c, border=bd_c)
    add_text(s2, cx + 0.18, 3.82, 2.4, 0.25, badge_c, size=9.2, color=col_c, bold=True)
    add_text(s2, cx + 0.18, 4.08, 2.4, 0.3, title_c, size=12.5, color=INK_DARK, bold=True)
    add_text(s2, cx + 0.18, 4.42, 2.4, 0.65, desc_c, size=9.2, color=INK_BODY if is_active else INK_MUTED)
    cx += 2.99

# 하단 본 보고서 핵심 질문 요약 바
add_left_accent_card(s2, 0.8, 5.4, 11.733, 1.05, BLUE_ACCENT)
add_text(s2, 1.05, 5.52, 11.2, 0.85, [
    ("🎯 본 보고서가 답하는 3대 핵심 질문", {"size": 11.5, "bold": True, "color": INK_DARK}),
    ("① [데이터 신뢰성] 1,152만 건 원천 중 왜 38.4%를 연쇄 격리했으며, 남은 496,863건은 청구-수납 차액 0원(100% 일치)인가?  ② [병목 원인] 차액이 0원인데 왜 피크타임(08~14시) 창구는 과부하에 빠지는가?  ③ [해결책] 통합 대시보드와 조건부 재확인으로 작업시간을 얼마나 줄일 수 있는가?", {"size": 10.0, "color": INK_BODY})
])


# ==============================================================================
# SLIDE 03: 2.1. 해당 데이터에 대한 기술 — 데이터 성격, 구조 및 크기
# ==============================================================================
s3 = create_light_slide(
    "2. DATA ENGINEERING · 2.1 SPECIFICATION",
    "2.1. 해당 데이터에 대한 기술 — 수납·대사 데이터 성격 , 구조 및 크기",
    "전사 17개 테이블(1,152만 건) 중 진료·처치·수납·환불로 이어지는 재무 대사 핵심 테이블과 시나리오 데이터셋입니다.",
    "팀 3 · 2.1 데이터 기술 (수납·대사 구조 및 크기)", 3
)

# 상단 3개 요약 카드
spec_cards = [
    ("데이터 성격 (What)", "외래 진료·수납·환불 대사 데이터", "진료 1건(encounters) 당 처치 3건(services)과 결제·환불 복수 거래(payments) 및 창구 작업시간 시나리오 결합"),
    ("전체 데이터 크기 (Scale)", "원천 1,152만 건 / 수납 150.7만 건", "17개 원천 테이블 11,522,242행 중 완료 진료 496,863건 · 수납 거래 732,464건 최종 정제 적재"),
    ("관계형 구조 (ERD Structure)", "1:N 수납 거래 및 자기참조(Self-FK)", "진료(1) ➔ 처치(3) & 진료(1) ➔ 결제·환불(N) 구조 및 환불 ➔ 원결제(original_payment_id) 역추적 구조")
]
sx = 0.8
for k_label, k_title, k_desc in spec_cards:
    add_card(s3, sx, 1.9, 3.75, 1.25, fill=WHITE, border=CARD_BORDER)
    add_text(s3, sx + 0.2, 2.02, 3.35, 0.22, k_label, size=9, color=LIGHT_PILL_FG, bold=True)
    add_text(s3, sx + 0.2, 2.26, 3.35, 0.3, k_title, size=13.5, color=INK_DARK, bold=True)
    add_text(s3, sx + 0.2, 2.60, 3.35, 0.45, k_desc, size=9.2, color=INK_MUTED)
    sx += 3.99

# 하단 테이블
rows_s3 = [
    ["핵심 테이블 / 데이터셋", "데이터 도메인", "원천 행 수 (Bronze)", "최종 정제 (Clean)", "수납 대사 프로세스상 역할 및 주요 식별자"],
    ["hospitals / departments", "의료기관·진료과 기준정보", "1,000 / 24 건", "485개 병원 / 12개 과", "병원 종별 및 병원-진료과목 마스터 (hospital_id, department_code)"],
    ["checkins", "원무 접수 트랜잭션", "2,010,000 건", "843,340 건", "예약 및 워크인 도착 확인, 상위 접수 외래키 (checkin_id, arrival_at)"],
    ["encounters", "임상 완료 진료 마스터", "1,000,000 건", "496,863 건", "진료 시작시각(08:00~14:59) 및 진료 단위 순청구액 기준 (encounter_id, net_charge)"],
    ["encounter_services", "진료별 처치·수가 상세", "2,980,326 건", "1,490,589 건", "진료 1건당 평균 3건 처치 수가 및 할인 합산 검증 (service_id, line_net_amount)"],
    ["payments (PAYMENT/REFUND)", "원무 수납·환불 트랜잭션", "1,507,501 건", "732,464 건", "단일·분할결제 및 부분 환불 거래, 원결제 추적 (payment_id, original_payment_id)"],
    ["collection_scenarios (합성실험)", "창구 작업단계 시뮬레이션", "표본 1,749 건", "작업 3,498 / 5,247건", "기본 2단계(수납+영수증) vs 복잡화 3단계(+재확인) 소요시간(분) 민감도 실험"]
]
add_clean_table(s3, 0.8, 3.35, 11.733, rows_s3, [2.3, 1.7, 1.5, 1.5, 4.733], row_h=0.43, font_size=9.5, highlight_col=3, highlight_color=INK_DARK)


# ==============================================================================
# SLIDE 04: 2.1. 수납·대사 메달리온 뷰 아키텍처 — MySQL Silver/Gold 뷰 10종 설계
# ==============================================================================
s4 = create_light_slide(
    "2. DATA ENGINEERING · 2.1 MEDALLION ARCHITECTURE",
    "2.1. 수납·대사 아키텍처 — MySQL 8.4 Silver(7종) · Gold(3종) 뷰 연계도",
    "원천 DB를 훼손하지 않고(Non-destructive), 거래 단위(Silver)를 진료 단위(Gold)로 통합 대사하는 10종의 표준 뷰를 구축했습니다.",
    "팀 3 · 2.1 수납·대사 메달리온 뷰 아키텍처 (Silver 7종 · Gold 3종)", 4
)

# 좌측: 차트/다이어그램 박스 (04_quarantine.png 활용)
add_card(s4, 0.8, 1.9, 5.7, 4.55, fill=WHITE, border=CARD_BORDER)
add_text(s4, 1.0, 2.02, 5.3, 0.3, "전체 데이터 정제 및 연쇄 격리(Cascade Quarantine) 현황", size=12, color=INK_DARK, bold=True)
if os.path.exists("pivot/charts/04_quarantine.png"):
    s4.shapes.add_picture("pivot/charts/04_quarantine.png", Inches(0.95), Inches(2.4), width=Inches(5.4))

# 우측 상단: Silver 7종 & Gold 3종 클러스터 설명 카드
add_left_accent_card(s4, 6.75, 1.9, 5.78, 2.05, TEAL_ACCENT)
add_text(s4, 7.0, 2.02, 5.4, 1.85, [
    ("🏗️ 수납·재정 대사 표준 뷰 10종 클러스터 (MySQL 8.4)", {"size": 12, "bold": True, "color": INK_DARK}),
    ("① Silver 정합성 검증 뷰 (7종): baek_silver_ encounters, encounter_services, payments, checkins, hospitals, departments, service_catalog", {"size": 9.8, "color": INK_BODY}),
    ("② Gold 진료단위 수납 마트: baek_gold_encounter_collection_mart (496,863건 1:1 통합)", {"size": 9.8, "color": INK_BODY}),
    ("③ Gold 환불 원결제 추적 뷰: baek_gold_refund_trace (환불 47,496건 한도 검증)", {"size": 9.8, "color": INK_BODY}),
    ("④ Gold 창구 수납 주제 마트: baek_gold_collection_topic (시간대·패턴별 부하 분석)", {"size": 9.8, "color": INK_BODY})
])

# 우측 중단: 연계 검증 테이블
rows_s4 = [
    ["메시지/뷰 검증 항목", "전수 규약 상태", "정합성 검증 결과"],
    ["처치 합산 = 진료 순청구액", "SUM(line_net) = net_charge", "496,863건 100% 일치"],
    ["결제합 - 환불합 = 순청구액", "paid - refund = net_charge", "차액 0원 (100% 일치)"],
    ["환불 ➔ 원결제(Self-FK) 추적", "original_payment_id 검증", "미연결·한도초과 0건"]
]
add_clean_table(s4, 6.75, 4.12, 5.78, rows_s4, [2.1, 1.98, 1.7], row_h=0.38, font_size=9.5, highlight_col=2, highlight_color=TEAL_ACCENT)

# 우측 하단: 설계 특징 콜아웃
add_left_accent_card(s4, 6.75, 5.75, 5.78, 0.7, RED_ACCENT)
add_text(s4, 7.0, 5.82, 5.4, 0.55, [
    [("💡 아키텍처 핵심 특징: ", {"size": 9.8, "bold": True, "color": INK_DARK}),
     ("개별 결제·환불 거래(73.2만 건)를 진료 1건(49.7만 건)으로 사전 집계하여, 창구 직원이 수기로 암산·대조하던 과정을 DB 뷰에서 100% 자동화했습니다.", {"size": 9.5, "color": INK_BODY})]
])


# ==============================================================================
# SLIDE 05: 2.2. Cleaning — 2단계 연쇄 격리(38.4%) 로직 및 무손실(Zero-Drop) 원칙
# ==============================================================================
s5 = create_light_slide(
    "2. DATA ENGINEERING · 2.2 CLEANING METHODOLOGY",
    "2.2. Cleaning — 2단계 연쇄 격리(38.4%) 로직 및 무손실(Zero-Drop) 분리",
    "원천 1,152만 건 중 왜 38.4%(약 442만 건)를 격리했는지, 부모-자식 외래키 도미노 격리 경위를 DB 실측으로 규명했습니다.",
    "팀 3 · 2.2 Cleaning (2단계 연쇄 격리 및 무손실 보존 원칙)", 5
)

# 상단 좌/우 카드
add_left_accent_card(s5, 0.8, 1.88, 5.7, 1.98, BLUE_ACCENT)
add_text(s5, 1.05, 1.96, 5.3, 1.82, [
    ("⚙️ 왜 1차(9.9%)가 아닌 누적 38.4%가 격리되었는가?", {"size": 11.5, "bold": True, "color": INK_DARK, "space_after": 3}),
    ("• 1단계 단일 테이블 격리(154만 건): 원천 1,152만 건 중 중복 재전송, 타임스탬프 역전, 더미 키(_999999999) 등 자체 결함 레코드 1차 분리.", {"size": 9.1, "color": INK_BODY, "space_after": 2}),
    ("• 2단계 부모-자식 연쇄 격리(Cascade, +288만 건): 상위 접수(checkins)·진료(encounters) 격리 시 하위 수납(67.9만)·처방(92.7만)도 도미노처럼 격리(reclean_quarantine) 보관.", {"size": 9.1, "color": INK_BODY, "space_after": 2}),
    ("• 핵심 방어: 무단 삭제(Drop)는 0건! 부모 진료가 깨진 수납만 살려두면 '유령 매출·가짜 미수금'이 발생하므로 연쇄 격리가 필수적임.", {"size": 9.1, "bold": True, "color": LIGHT_PILL_FG, "space_after": 0})
], line_spacing=1.18)

add_left_accent_card(s5, 6.8, 1.88, 5.733, 1.98, TEAL_ACCENT)
add_text(s5, 7.05, 1.96, 5.3, 1.82, [
    ("🛡️ 수납·대사 4대 무결성 정제 룰셋 요약", {"size": 11.5, "bold": True, "color": INK_DARK, "space_after": 3}),
    ("1. 더미·고아 외래키 차단: encounter_id, checkin_id가 _999999999이거나 상위 테이블에 없는 고아 수납 레코드 전수 격리", {"size": 9.1, "color": INK_BODY, "space_after": 2}),
    ("2. 부모-자식 도미노 정합성: FK_PARENT_QUARANTINED 규칙으로 격리된 진료에 속한 하위 결제·처방 레코드 동반 격리", {"size": 9.1, "color": INK_BODY, "space_after": 2}),
    ("3. 외래 운영시간(08:00~14:59) 정규화: 07시 이른 도착 및 부모 접수 결함 워크인 이상치를 격리하여 순수 외래 피크 시간대 확보", {"size": 9.1, "color": INK_BODY, "space_after": 2}),
    ("4. 환불 자기참조(Self-FK) 무결성: original_payment_id 누락 및 한도 초과 검증", {"size": 9.1, "color": INK_BODY, "space_after": 0})
], line_spacing=1.18)

# 하단 테이블
rows_s5 = [
    ["정제 단계 / 대상 테이블", "원천 행 수 (Bronze)", "1차 자체 결함 격리", "2차 부모키 연쇄 격리", "최종 Clean 적재", "주요 격리 사유 (reclean_quarantine 실측)"],
    ["전체 17개 테이블 합계", "11,522,242 건", "1,540,929 건", "약 2,880,000 건", "약 7,100,000 건", "누적 약 442만 건(38.4%) 격리 보관 (무단 Drop 0건)"],
    ["encounters (외래 진료)", "1,000,000 건", "373,832 건", "129,305 건", "496,863 건", "상위 접수(FK_PARENT_QUARANTINED:checkin_id) 결함 연쇄 격리"],
    ["payments (수납·환불)", "1,507,501 건", "95,305 건", "679,732 건", "732,464 건", "격리된 진료(encounter_id)에 종속된 하위 수납 도미노 격리"],
    ["encounter_services (처치)", "2,980,326 건", "562,673 건", "927,064 건", "1,490,589 건", "격리된 진료(encounter_id)에 종속된 하위 처치 도미노 격리"]
]
add_clean_table(s5, 0.8, 4.02, 11.733, rows_s5, [2.1, 1.55, 1.55, 1.65, 1.55, 3.333], row_h=0.43, font_size=9.5, highlight_col=4, highlight_color=INK_DARK)


# ==============================================================================
# SLIDE 06: 2.3. Cleaning 결과 — 최종 496,863건 재정 대사 100.0% 일치 (차액 0원)
# ==============================================================================
s6 = create_light_slide(
    "2. DATA ENGINEERING · 2.3 VALIDATION RESULTS",
    "2.3. Cleaning 결과 — 496,863건 재정 대사 100.0% 일치 (차액 0원 입증)",
    "불량·연쇄결함 38.4%를 격리한 뒤 남은 최종 완료 진료 496,863건은 청구액과 순수납액이 단 1원의 오차도 없이 100% 일치합니다.",
    "팀 3 · 2.3 Cleaning 결과 (청구-수납 100.0% 일치 및 12대 교차검증)", 6
)

# 상단 4개 대형 KPI 카드 (PDF Slide 06 레이아웃 100% 동일)
kpis_s6 = [
    ("496,863 건", "최종 검증 완료 진료 (Clean)", INK_DARK),
    ("732,464 건", "최종 수납·환불 거래 (Payments)", INK_DARK),
    ("193.8 억 원", "순청구액 = 순수납액 (19,381,620,860원)", INK_DARK),
    ("100.0 %", "청구-수납 재정 대사 일치율 (차액 0원)", TEAL_ACCENT)
]
kx = 0.8
for k_num, k_sub, k_col in kpis_s6:
    add_card(s6, kx, 1.9, 2.75, 1.15, fill=WHITE, border=CARD_BORDER)
    add_text(s6, kx + 0.2, 2.05, 2.35, 0.45, k_num, size=22, color=k_col, bold=True)
    add_text(s6, kx + 0.2, 2.58, 2.35, 0.3, k_sub, size=9.2, color=INK_MUTED)
    kx += 2.99

# 하단 좌측: 테이블
rows_s6 = [
    ["재정 대사 검증 항목 (Gold 마트 실측)", "실측 수치 / 금액", "정합성 검증 결과"],
    ["완료 진료 순청구액 합계 (net_charge)", "19,381,620,860 원", "처치(149만 건) 합계와 100% 일치"],
    ["결제 총합 (PAYMENT 684,968건)", "19,568,700,200 원", "단일 26.1만 + 분할 18.8만 진료"],
    ["환불 총합 (REFUND 47,496건)", "187,079,340 원", "원결제(Self-FK) 100% 정상 연결"],
    ["순수납액 (결제 총합 - 환불 총합)", "19,381,620,860 원", "순청구액과 차액 0원 (100% 일치)"],
    ["금액 불일치 / 결제 누락 / 한도 초과", "0 건 / 0 건 / 0 건", "12대 교차검증 테스트 전항목 PASS"]
]
add_clean_table(s6, 0.8, 3.3, 6.2, rows_s6, [2.5, 1.8, 1.9], row_h=0.45, font_size=9.5, highlight_col=2, highlight_color=TEAL_ACCENT)

# 하단 우측: 결론 콜아웃 박스
add_left_accent_card(s6, 7.25, 3.3, 5.28, 3.15, TEAL_ACCENT)
add_text(s6, 7.5, 3.48, 4.85, 2.8, [
    ("🏆 재정 대사 무결성 최종 검토 결론 (관점 전환의 근거)", {"size": 12.5, "bold": True, "color": INK_DARK}),
    ("• 금전적 누락·오류 0건 입증: 정제 후 완료 진료 496,863건을 전수 대사한 결과, 총 결제액(195.69억)에서 환불액(1.87억)을 뺀 순수납액은 순청구액(193.82억)과 단 1원의 차액도 없이 100.0% 일치합니다.", {"size": 9.8, "color": INK_BODY}),
    ("• 왜곡 없는 정직한 데이터 해석: 데이터에 존재하지도 않는 '미수금 사고'나 '계산 오류'를 억지로 꾸며내지 않았습니다.", {"size": 9.8, "color": INK_BODY}),
    ("• 진짜 문제는 '창구 확인 과정의 물량과 복잡도': 결과적으로 돈은 맞지만, 이 차액 0원을 맞추기 위해 창구 직원이 분할결제(37.86%)와 환불(9.56%) 복수 거래를 묶어 대조해야 하는 '업무 복잡도'가 핵심 병목입니다.", {"size": 9.8, "bold": True, "color": LIGHT_PILL_FG})
])


# ==============================================================================
# SLIDE 07: 3. 분석 — 진료의 절반(47.4%)이 복수 거래 합산·원결제 추적 대상이다 (Funnel)
# ==============================================================================
s7 = create_light_slide(
    "3. ANALYSIS · BILLING WORKLOAD FUNNEL",
    "3. 분석 — 돈은 100% 맞지만 , 진료의 47.4%(23.5만 건)가 복수 거래 확인 대상이다",
    "완료 진료 49.7만 건의 수납 거래 퍼널을 분석한 결과, 창구 과부하의 원인은 '금액 오류'가 아니라 '분할·환불 합산 대조 물량'이었습니다.",
    "팀 3 · 3. 분석 (수납 거래 구조 및 복수 거래 퍼널 분석)", 7
)

# 상단 5단계 퍼널 카드 (PDF Slide 07과 100% 동일한 구성, 3번째 레드 하이라이트)
funnel_steps = [
    ("STEP 1. 완료 진료", "49.7 만 건", "처치 149.1만 건 (진료당 3건)", False),
    ("STEP 2. 총 수납 거래", "73.2 만 건", "결제 68.5만 + 환불 4.7만 건", False),
    ("🚨 복수 거래 합산·추적", "23.5 만 건", "전체 진료의 47.4% 창구 확인 집중", True),
    ("분할결제 (2회 이상)", "18.8 만 건", "진료의 37.86% (전표 합산 대조)", False),
    ("환불 발생 (원결제 추적)", "4.7 만 건", "진료의 9.56% (승인·한도 역추적)", False)
]
fx = 0.8
for f_top, f_big, f_sub, is_red in funnel_steps:
    f_fill = RED_SOFT_BG if is_red else WHITE
    f_bd = RED_SOFT_BD if is_red else CARD_BORDER
    top_col = RED_ACCENT if is_red else LIGHT_PILL_FG
    big_col = RED_ACCENT if is_red else INK_DARK
    sub_col = RED_ACCENT if is_red else INK_MUTED
    add_card(s7, fx, 1.9, 2.22, 1.45, fill=f_fill, border=f_bd)
    add_text(s7, fx + 0.1, 2.02, 2.02, 0.25, f_top, size=9, color=top_col, bold=True, align=PP_ALIGN.CENTER)
    add_text(s7, fx + 0.1, 2.32, 2.02, 0.50, f_big, size=20, color=big_col, bold=True, align=PP_ALIGN.CENTER)
    add_text(s7, fx + 0.1, 2.88, 2.02, 0.35, f_sub, size=8.8, color=sub_col, bold=(is_red), align=PP_ALIGN.CENTER)
    fx += 2.38

# 하단 콜아웃 박스 + 우측 차트(차트 1)
add_left_accent_card(s7, 0.8, 3.6, 6.2, 2.85, RED_ACCENT)
add_text(s7, 1.05, 3.75, 5.75, 2.55, [
    ("🎯 차액이 0원인데 왜 복수 거래 집계가 창구의 구조적 부담인가?", {"size": 12.5, "bold": True, "color": INK_DARK}),
    ("• 단일 결제(52.58%, 26.1만 건): 진료 1건당 결제 1건(1:1)으로 청구액과 결제액이 즉시 일치하므로 직원의 추가 대조가 필요 없습니다.", {"size": 9.8, "color": INK_BODY}),
    ("• 분할 결제(37.86%, 18.8만 건): 환자 1명이 여러 카드·현금으로 나누어 결제(진료당 평균 2.0건)하므로, 레거시 화면에서 흩어진 승인 전표들을 진료 1건 단위로 묶어 합계가 맞는지 일일이 확인해야 합니다.", {"size": 9.8, "color": INK_BODY}),
    ("• 환불 거래(9.56%, 4.7만 건): 단순 취소가 아니라 과거 어떤 원결제(original_payment_id)에서 얼마를 환불했는지 승인번호와 잔여 한도를 역추적해야 하므로 확인 시간이 배가됩니다.", {"size": 9.8, "color": INK_BODY})
])

add_card(s7, 7.2, 3.6, 5.333, 2.85, fill=WHITE, border=CARD_BORDER)
if os.path.exists("docs/notion_charts/차트_1_수납패턴별_진료비중_및_복수거래_분석.png"):
    s7.shapes.add_picture("docs/notion_charts/차트_1_수납패턴별_진료비중_및_복수거래_분석.png", Inches(7.32), Inches(3.72), width=Inches(5.1))


# ==============================================================================
# SLIDE 08: 3. 분석 — 피크 시간대(08~14시)에 외래 물량 83.5%와 분할·환불이 쏠린다
# ==============================================================================
s8 = create_light_slide(
    "3. ANALYSIS · PEAK HOUR CONCENTRATION",
    "3. 분석 — 09~13시에 물량 83.5%가 몰리고 , 08시 분할 · 14시 환불이 터진다",
    "진료 시작 시간대(08:00~14:59)별 수납 패턴을 분석한 결과, 실제 병원 외래 운영 주기와 완벽히 일치하는 시간대별 병목이 확인되었습니다.",
    "팀 3 · 3. 분석 (시간대별 외래 수납 물량 및 분할·환불 집중도)", 8
)

# 좌측: 차트 카드 (차트 2)
add_card(s8, 0.8, 1.9, 6.3, 4.55, fill=WHITE, border=CARD_BORDER)
add_text(s8, 1.0, 2.02, 5.9, 0.3, "시간대별 완료 진료 건수 및 분할결제·복수거래 집중 현황 (08시~14시)", size=11.5, color=INK_DARK, bold=True)
if os.path.exists("docs/notion_charts/차트_2_피크시간대_08_14시_복수거래_집중현황.png"):
    s8.shapes.add_picture("docs/notion_charts/차트_2_피크시간대_08_14시_복수거래_집중현황.png", Inches(0.95), Inches(2.45), width=Inches(6.0))

# 우측 상단: 시간대별 구간 테이블 (PDF Slide 08 우측 상단 표 레이아웃과 100% 동일)
rows_s8 = [
    ["수납 시간대 구간", "완료 진료 건수", "분할결제 비율", "환불 발생 비율", "병원 원무 운영 특성"],
    ["08시 (08:00~08:59)", "48,695 건 (9.8%)", "60.45 % (최고)", "6.88 %", "아침 채혈·검사 선수납 및 추가수납"],
    ["09~13시 (5시간 피크)", "414,860 건 (83.5%)", "36.11 %", "9.32 %", "오전~오후 초입 외래 수납 대란 구간"],
    ["14시 (14:00~14:59)", "33,308 건 (6.7%)", "26.64 %", "16.25 % (최고)", "오후 검사 취소·처방 변경·퇴원 정산"]
]
add_clean_table(s8, 7.3, 1.9, 5.233, rows_s8, [1.15, 1.15, 0.95, 0.9, 1.083], row_h=0.52, font_size=8.8, highlight_col=2, highlight_color=INK_DARK)

# 우측 하단: 데이터 분석 결론 콜아웃 (PDF Slide 08 우측 하단 카드와 100% 동일)
add_left_accent_card(s8, 7.3, 4.25, 5.233, 2.2, BLUE_ACCENT)
add_text(s8, 7.55, 4.38, 4.85, 1.95, [
    ("💡 피크 시간대(08:00~14:59) 데이터 분석 결론", {"size": 11.5, "bold": True, "color": INK_DARK}),
    ("• 왜 24시간이 아닌 08~14시인가?: 응급실(ER)이 아닌 '외래(Outpatient) 진료 시작 시각' 기준이며, 07시 이른 도착 및 접수 결함 워크인이 정제 단계에서 격리되어 실제 병원 외래 골든타임(08~14시)만 남았습니다.", {"size": 9.3, "color": INK_BODY}),
    ("• 3대 시간대별 병목: ① 08시 분할결제 피크(60.45%), ② 09~13시 전체 외래 물량 83.5% 집중, ③ 14시 환불 피크(16.25%)로 시간대별 맞춤형 창구 대응이 필수적입니다.", {"size": 9.3, "color": INK_BODY})
])


# ==============================================================================
# SLIDE 09: 3. 분석 — 전수 재확인 시 작업시간 +124% 폭증, 조건부 재확인으로 21.5인일 절감
# ==============================================================================
s9 = create_light_slide(
    "3. ANALYSIS · WORKLOAD SIMULATION",
    "3. 분석 — 전수 재확인은 +124% 폭증 , 조건부 축소는 21.5인일 절감",
    "동일 결제 표본 1,749건 시나리오 실험 결과, 96.4% 정상 거래에 대한 반복 재확인을 생략하는 것이 핵심 해법임이 입증되었습니다.",
    "팀 3 · 3. 분석 (수납 복잡화 시나리오 및 조건부 재확인 시뮬레이션 성과)", 9
)

# 상단 좌측 차트 1: 작업량 폭증 비교 (차트 3)
add_card(s9, 0.8, 1.9, 5.7, 2.85, fill=WHITE, border=CARD_BORDER)
if os.path.exists("docs/notion_charts/차트_3_수납복잡화_시나리오_작업시간_절감효과.png"):
    s9.shapes.add_picture("docs/notion_charts/차트_3_수납복잡화_시나리오_작업시간_절감효과.png", Inches(1.25), Inches(1.96), height=Inches(2.68))

# 상단 우측 차트 2: 대사 근거 분류 (02_evidence.png)
add_card(s9, 6.8, 1.9, 5.733, 2.85, fill=WHITE, border=CARD_BORDER)
if os.path.exists("baek/offline_topic_analysis_20261015/charts/02_evidence.png"):
    s9.shapes.add_picture("baek/offline_topic_analysis_20261015/charts/02_evidence.png", Inches(7.25), Inches(1.96), height=Inches(2.68))

# 하단 성과 요약 테이블 (PDF Slide 09 하단 표 레이아웃과 100% 동일)
rows_s9 = [
    ["핵심 성과 지표 (표본 1,749건 · 일 6시간=360분 인일 기준)", "기본 2단계 (BASE)", "전수 재확인 (3단계 복잡화)", "조건부 재확인 적용 (TO-BE 개선 성과)"],
    ["창구 수행 작업 수 (수납 + 영수증 + 재확인)", "3,498 작업 (건당 2단계)", "5,247 작업 (1.5배 증가)", "▼ 반복 재확인 50% 축소 시 4,373 작업"],
    ["창구 총 작업 소요시간 및 필요 인일(Man-Day)", "20,937 분 (58.2 인일)", "46,920 분 (130.3 인일, +124.1%)", "▼ 39,162.8 분 (-7,757.3분 / -21.5 인일 절감)"],
    ["과거 로컬 기준 점검 시 실제 수동 확인 대상", "전체 1,749 건", "정상 일치 1,686 건 (96.4% 자동통과)", "▼ 실제 점검 대상 63건(차이 19+보류 44)으로 -96.4% 압축"]
]
add_clean_table(s9, 0.8, 4.92, 11.733, rows_s9, [3.6, 2.3, 2.6, 3.233], row_h=0.41, font_size=9.3, highlight_col=3, highlight_color=TEAL_ACCENT)


# ==============================================================================
# SLIDE 10: 4. 결론 — 다섯 가지 제안 : 데이터가 증명한 원무 수납 액션 로드맵
# ==============================================================================
s10 = create_light_slide(
    "4. CONCLUSION · ACTION PLAN",
    "4. 결론 — 다섯 가지 제안 : 데이터가 증명한 원무 수납 액션 로드맵",
    "왼쪽이 구체적 실행 방안이며 , 오른쪽이 데이터 분석 및 시뮬레이션을 통해 도출된 핵심 근거 수치입니다 .",
    "팀 3 · 4. 결론 (원무 수납 다섯 가지 제안)", 10
)

actions = [
    ("1", "진료 단위 통합 대사 대시보드(UI) 전면 도입 — 『직원이 보는 화면 개선』",
     "개별 거래로 흩어진 분할결제·환불 내역을 진료 1건(encounter_id) 단위로 묶어 [청구액·결제합·환불합·차액 0원·원결제 한도]를 한 화면에 자동 표시함.",
     "23.5만 건 (47.4%)", "복수 거래 합산 대조 자동화", INK_DARK),
    ("2", "조건부 재확인(Smart Filtering Rule) 규정 수립 — 『일하는 프로세스 혁신』",
     "대시보드가 [차액=0원 & 원결제 정상]으로 자동 판정한 96.4%의 정상 거래는 2차 수기 재확인(RECHECK)을 면제하고, 차이·보류(3.6%)만 선별 점검함.",
     "-7,757분 (21.5인일)", "재확인 50% 축소 시 즉시 절감", TEAL_ACCENT),
    ("3", "08시 분할결제 피크(60.5%) 및 09~13시 외래 집중(83.5%) 키오스크·모바일 분산",
     "단건 일치 진료(52.6%)는 키오스크·모바일 수납으로 즉시 유도하고, 대면 창구는 분할결제·환불 집중 시간대(08시, 09~13시) 전담 창구로 탄력 운영함.",
     "83.5% / 60.5%", "오전 물량 집중 / 08시 분할 피크", TEAL_ACCENT),
    ("4", "14시 환불 집중 구간(16.25%) 원결제(Self-FK) 한도 자동 검증 가드레일 적용",
     "오후 퇴원·검사 취소 환불이 몰리는 14시 구간에 baek_gold_refund_trace 뷰를 연동하여 원결제 승인번호 및 잔여 환불 가능 한도를 실시간 자동 검증함.",
     "47,496 건 (100%)", "환불 원결제 연결 및 한도 무결성", INK_DARK),
    ("5", "2단계 연쇄 격리(38.4%) 아키텍처 상시화로 유령 매출 차단 및 AI 예측 마트 공급",
     "부모키 결함 데이터의 도미노 격리(reclean_quarantine)를 표준 파이프라인화하여 재정 정합도 100%의 Gold 마트를 피크타임 혼잡도 AI 예측 모델에 공급함.",
     "100.0% (차액 0원)", "청구-수납 최종 재정 대사 정합도", INK_DARK)
]

ay = 1.9
for num_s, act_title, act_desc, metric_val, metric_lbl, m_col in actions:
    add_card(s10, 0.8, ay, 11.733, 0.84, fill=WHITE, border=CARD_BORDER)
    # 파란색 번호 배지
    num_box = add_card(s10, 0.98, ay + 0.21, 0.42, 0.42, fill=LIGHT_PILL_FG, border=None, rounded=True, adj=0.2)
    add_text(s10, 0.98, ay + 0.21, 0.42, 0.42, num_s, size=12, color=WHITE, bold=True, align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)
    # 좌측 액션 제목 & 설명
    add_text(s10, 1.58, ay + 0.12, 7.8, 0.3, act_title, size=11.5, color=INK_DARK, bold=True)
    add_text(s10, 1.58, ay + 0.44, 7.8, 0.3, act_desc, size=9.2, color=INK_MUTED)
    # 우측 핵심 지표
    add_text(s10, 9.5, ay + 0.14, 2.8, 0.32, metric_val, size=13, color=m_col, bold=True, align=PP_ALIGN.RIGHT)
    add_text(s10, 9.5, ay + 0.46, 2.8, 0.25, metric_lbl, size=8.8, color=INK_MUTED, align=PP_ALIGN.RIGHT)
    ay += 0.94


# ==============================================================================
# SLIDE 11: 4. 결론 — 이 보고서가 말하지 않는 것 (한계점과 향후 보완점) (Dark Theme)
# ==============================================================================
s11 = create_dark_slide(
    "4. CONCLUSION · LIMITATIONS",
    "이 보고서가 말하지 않는 것 (한계점과 향후 보완점)",
    "팀 3 · 4. 결론 (한계점 및 보완점 — 수납·재무 파트)", 11
)

lim_cards = [
    ("• 현장에 금전적 손실(미수금 사고)이 발생했다고 주장하지 않는다: ",
     "최종 정제된 완료 진료 496,863건은 청구액과 순수납액의 차액이 0원(100% 일치)입니다. 본 보고서는 회계적 오류를 주장하는 것이 아니라, 그 차액 0원을 유지하기 위해 창구 직원이 감당하는 '복수 거래 합산 대조(23.5만 건)와 반복 재확인 과정의 물리적 부하'를 규명한 것입니다."),
    ("• 작업시간 폭증(+124.1%)은 실제 병원 실측 로그가 아닌 시나리오 실험이다: ",
     "원본 EMR 테이블에는 결제 금액과 시각만 존재하고 직원의 처리 시간(분) 로그가 없습니다. 따라서 동일 결제 1,749건에 작업 단계(2단계 vs 3단계 재확인)를 부여한 합성 시나리오를 통해 '과잉 재확인 규정이 도입될 때의 민감도 상한선(Upper Bound)'을 모델링한 것입니다."),
    ("• 구버전 로컬 파일의 불일치(19건)·보류(44건)를 최종 DB의 결함으로 해석하지 않는다: ",
     "표본 1,749건의 차이(1.09%)와 보류(2.52%)는 과거 로컬 입력 기준에서 대사 근거가 불완전할 때 점검 대상을 어떻게 분리하는지 보여주는 절차적 예시이며, 최종 MySQL DB와는 엄격히 구분하여 해석해야 합니다.")
]

ly = 1.65
for lead_t, body_t in lim_cards:
    add_card(s11, 0.8, ly, 11.733, 1.05, fill=DARK_CARD, border=DARK_BORDER, rounded=True, adj=0.06)
    add_text(s11, 1.05, ly + 0.18, 11.2, 0.75, [
        [(lead_t, {"size": 10.5, "bold": True, "color": TEAL_BRIGHT}),
         (body_t, {"size": 10.2, "color": WHITE})]
    ])
    ly += 1.22

# 하단 보완 과제 박스
add_card(s11, 0.8, 5.4, 11.733, 0.95, fill=DARK_CARD, border=DARK_BORDER, rounded=True, adj=0.08)
add_text(s11, 1.05, 5.52, 11.2, 0.7, [
    ("🔮 다음에 검증할 보완 과제", {"size": 11, "bold": True, "color": TEAL_BRIGHT}),
    ("① 실제 원무 창구 키오스크·대면 수납 타임스탬프 로그 결합 실측 ② 시간대(08~14시)·진료과별 창구 대기시간 예측 AI 모델 학습 ③ 진료비 구간 및 결제수단 조합별 세분화된 동적 재확인(Dynamic Recheck) 임계값 고도화", {"size": 10, "color": WHITE})
])


# ==============================================================================
# SLIDE 12: EXECUTIVE EPILOGUE — 한 장으로 다시 (Dark Theme)
# ==============================================================================
s12 = create_dark_slide(
    "EXECUTIVE EPILOGUE",
    "한 장으로 다시",
    "분석 대상: 전국 485개 병원 정제 EMR 데이터베이스 (원천 1,152만 건 중 38.4% 연쇄 격리 제외 · 완료 진료 496,863건)",
    "Slide 12 · End of Report"
)

add_text(s12, 0.8, 1.75, 11.5, 1.4, [
    [("원천 1,152만 건 중 부모키가 깨진 38.4%를 연쇄 격리한 뒤 남은 ", {"size": 13.5, "color": DARK_SUB}),
     ("496,863건의 진료는 차액 0원으로 100% 일치했습니다 .", {"size": 13.5, "bold": True, "color": WHITE})],
    [("하지만 그 완벽한 정산 뒤에는 오전 피크타임(09~13시)에 몰리는 ", {"size": 13.5, "color": DARK_SUB}),
     ("83.5%의 외래 물량과 23.5만 건의 분할·환불 거래가 있었습니다 .", {"size": 13.5, "bold": True, "color": DARK_SUB})],
    [("문제의 본질은 돈이 틀린 것이 아니라 ", {"size": 13.5, "color": DARK_SUB}),
     ("‘흩어진 복수 거래를 수기로 묶어 확인하는 창구의 복잡도(+124.1% 폭증)’", {"size": 13.5, "bold": True, "color": WHITE}),
     ("였습니다 .", {"size": 13.5, "color": DARK_SUB})]
], line_spacing=1.45)

add_text(s12, 0.8, 3.55, 11.5, 0.95, [
    ("진료 단위 통합 대사 대시보드(UI)로 흩어진 결제·환불을 한 화면에 묶고 ,", {"size": 15.5, "bold": True, "color": TEAL_BRIGHT}),
    ("조건부 재확인(Rule)으로 불필요한 반복 확인을 절반만 줄여도 7,757분(21.5인일)의 창구 부하가 즉시 사라집니다 .", {"size": 15.5, "bold": True, "color": TEAL_BRIGHT})
], line_spacing=1.4)

add_card(s12, 0.8, 4.9, 10.6, 1.15, fill=DARK_CARD, border=DARK_BORDER, rounded=True, adj=0.08)
add_text(s12, 1.1, 5.12, 10.0, 0.75, [
    ("가장 먼저 — 진료 단위 통합 대사 대시보드로 23.5만 건의 분할·환불 조회를 단일 화면으로 통합하고 ,", {"size": 12, "bold": True, "color": TEAL_BRIGHT}),
    ("조건부 재확인 규칙을 통해 96.4% 정상 거래의 수기 재확인을 면제하여 피크타임 수납 창구의 병목을 완전히 해소합니다 .", {"size": 12, "bold": True, "color": WHITE})
], line_spacing=1.35)


# ==============================================================================
# 저장 및 PDF 자동 변환
# ==============================================================================
pptx_out = os.path.abspath("pivot/소주제_수납대사검증_및_창구업무복잡도최적화_12장.pptx")
pdf_out  = os.path.abspath("pivot/소주제_수납대사검증_및_창구업무복잡도최적화_12장.pdf")
prs.save(pptx_out)
print(f"[OK] Saved PPTX: {pptx_out}")
