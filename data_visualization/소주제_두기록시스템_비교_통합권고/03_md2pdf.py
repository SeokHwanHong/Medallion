# -*- coding: utf-8 -*-
# [황유민] Markdown(표, 목록, 코드, 그림 ![](경로), <!-- pagebreak -->) -> PDF (reportlab, 맑은 고딕)
# 실행: python -I 03_md2pdf.py <입력.md> <출력.pdf> "<꼬리말 제목>"
import re, sys
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (CondPageBreak, BaseDocTemplate, PageTemplate, Frame, Paragraph, Spacer, Table, TableStyle,
                                PageBreak, KeepTogether, Preformatted, HRFlowable)

src, dst = sys.argv[1], sys.argv[2]
TITLE = sys.argv[3] if len(sys.argv) > 3 else ''
import os
from reportlab.platypus import Image
from reportlab.lib.utils import ImageReader
pdfmetrics.registerFont(TTFont('MG', 'C:/Windows/Fonts/malgun.ttf'))
pdfmetrics.registerFont(TTFont('MGB', 'C:/Windows/Fonts/malgunbd.ttf'))
pdfmetrics.registerFontFamily('MG', normal='MG', bold='MGB', italic='MG', boldItalic='MGB')

INK = colors.HexColor('#1f2933'); MUTE = colors.HexColor('#616e7c'); ACC = colors.HexColor('#1d4e89')
HEAD = colors.HexColor('#e8eef6'); LINE = colors.HexColor('#c5ced8'); CODEBG = colors.HexColor('#f3f5f7')

S = dict(
    h1=ParagraphStyle('h1', fontName='MGB', fontSize=19, leading=25, textColor=ACC, spaceAfter=6),
    h2=ParagraphStyle('h2', fontName='MGB', fontSize=14, leading=19, textColor=ACC, spaceBefore=12, spaceAfter=5),
    h3=ParagraphStyle('h3', fontName='MGB', fontSize=11.2, leading=15, textColor=INK, spaceBefore=9, spaceAfter=3),
    p=ParagraphStyle('p', fontName='MG', fontSize=9, leading=13.6, textColor=INK, spaceAfter=3.5),
    li=ParagraphStyle('li', fontName='MG', fontSize=9, leading=13.4, textColor=INK, leftIndent=16, bulletIndent=2, spaceAfter=1.8),
    li2=ParagraphStyle('li2', fontName='MG', fontSize=9, leading=13.4, textColor=INK, leftIndent=26, bulletIndent=16, spaceAfter=1.5),
    quote=ParagraphStyle('q', fontName='MG', fontSize=8.8, leading=13, textColor=MUTE, leftIndent=10, borderPadding=(3, 3, 3, 6), spaceAfter=4),
    cell=ParagraphStyle('c', fontName='MG', fontSize=7.8, leading=10.6, textColor=INK),
    cellh=ParagraphStyle('ch', fontName='MGB', fontSize=7.8, leading=10.6, textColor=INK),
    code=ParagraphStyle('code', fontName='MG', fontSize=7.8, leading=10.8, textColor=INK),
)

def esc(t):
    return t.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')

def inline(t):
    t = esc(t)
    t = re.sub(r'`([^`]+)`', lambda m: f'<font backColor="#eceff3" color="#8a2d3b">{m.group(1)}</font>', t)
    t = re.sub(r'\*\*([^*]+)\*\*', r'<b>\1</b>', t)
    return t

def split_row(line):
    line = line.strip()
    if line.startswith('|'): line = line[1:]
    if line.endswith('|'): line = line[:-1]
    cells, cur, i = [], '', 0
    while i < len(line):
        ch = line[i]
        if ch == '\\' and i + 1 < len(line) and line[i + 1] == '|':
            cur += '|'; i += 2; continue
        if ch == '`':   # 코드 안의 | 는 구분자가 아님
            j = line.find('`', i + 1)
            if j != -1:
                cur += line[i:j + 1]; i = j + 1; continue
        if ch == '|':
            cells.append(cur.strip()); cur = ''
        else:
            cur += ch
        i += 1
    cells.append(cur.strip())
    return cells

W_AVAIL = A4[0] - 28 * mm

def make_table(rows):
    hdr, body = rows[0], rows[1:]
    n = len(hdr)
    body = [r + [''] * (n - len(r)) if len(r) < n else r[:n] for r in body]
    # 열 너비: 내용 길이 기반 (최소/최대 보정)
    lens = []
    for c in range(n):
        m = max([len(re.sub(r'[`*]', '', hdr[c]))] + [min(len(re.sub(r'[`*]', '', r[c])), 60) for r in body] + [3])
        lens.append(max(m, 4) ** 0.85)
    tot = sum(lens)
    widths = [W_AVAIL * l / tot for l in lens]
    data = [[Paragraph(inline(h), S['cellh']) for h in hdr]] + [[Paragraph(inline(c), S['cell']) for c in r] for r in body]
    t = Table(data, colWidths=widths, repeatRows=1)
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), HEAD),
        ('GRID', (0, 0), (-1, -1), 0.4, LINE),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 3.5), ('RIGHTPADDING', (0, 0), (-1, -1), 3.5),
        ('TOPPADDING', (0, 0), (-1, -1), 2.5), ('BOTTOMPADDING', (0, 0), (-1, -1), 2.5),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8fafc')]),
    ]))
    return t

lines = open(src, encoding='utf-8').read().split('\n')
story, i = [], 0
first_h1 = True
while i < len(lines):
    ln = lines[i]
    if ln.strip() == '':
        i += 1; continue
    m = re.match(r'^!\[(.*?)\]\((.*?)\)', ln)
    if m:
        pth = os.path.join(os.path.dirname(os.path.abspath(src)), m.group(2))
        iw, ih = ImageReader(pth).getSize()
        w = W_AVAIL
        story += [Image(pth, width=w, height=w * ih / iw), Spacer(1, 6)]
        i += 1; continue
    if ln.strip() == '<!-- pagebreak -->':
        story.append(PageBreak()); i += 1; continue
    if ln.startswith('```'):
        i += 1; buf = []
        while i < len(lines) and not lines[i].startswith('```'):
            buf.append(lines[i]); i += 1
        i += 1
        pre = Preformatted('\n'.join(buf), S['code'])
        t = Table([[pre]], colWidths=[W_AVAIL])
        t.setStyle(TableStyle([('BACKGROUND', (0, 0), (-1, -1), CODEBG), ('BOX', (0, 0), (-1, -1), 0.4, LINE),
                               ('LEFTPADDING', (0, 0), (-1, -1), 6), ('TOPPADDING', (0, 0), (-1, -1), 4), ('BOTTOMPADDING', (0, 0), (-1, -1), 4)]))
        story += [t, Spacer(1, 5)]
        continue
    if ln.startswith('|'):
        rows = []
        while i < len(lines) and lines[i].startswith('|'):
            r = split_row(lines[i])
            if not all(re.fullmatch(r':?-{2,}:?', c) for c in r):
                rows.append(r)
            i += 1
        story += [make_table(rows), Spacer(1, 6)]
        continue
    if ln.startswith('---'):
        story += [HRFlowable(width='100%', thickness=0.5, color=LINE, spaceBefore=4, spaceAfter=4)]
        i += 1; continue
    m = re.match(r'^(#{1,3}) (.*)', ln)
    if m:
        lvl = len(m.group(1)); txt = inline(m.group(2))
        if lvl == 2 and not first_h1 and False:
            story.append(PageBreak())
        if lvl == 2:
            story.append(CondPageBreak(60 * mm))
        story.append(Paragraph(txt, S['h%d' % lvl]))
        if lvl == 1:
            story.append(HRFlowable(width='100%', thickness=1.2, color=ACC, spaceAfter=6))
        i += 1; continue
    if ln.startswith('>'):
        buf = []
        while i < len(lines) and lines[i].startswith('>'):
            buf.append(lines[i].lstrip('> ').strip()); i += 1
        story.append(Paragraph(inline(' '.join(buf)), S['quote']))
        continue
    m = re.match(r'^(\s*)- (\[[ x]\] )?(.*)', ln)
    if m:
        ind = len(m.group(1)); box = m.group(2)
        bullet = ('[ ]' if box and box.strip() == '[ ]' else '[v]') if box else '•'
        story.append(Paragraph(inline(m.group(3)), S['li2'] if ind >= 2 else S['li'], bulletText=bullet))
        i += 1; continue
    m = re.match(r'^(\s*)(\d+)\. (.*)', ln)
    if m:
        story.append(Paragraph(inline(m.group(3)), S['li'], bulletText=m.group(2) + '.'))
        i += 1; continue
    # 일반 문단
    buf = [ln.strip()]; i += 1
    while i < len(lines) and lines[i].strip() and not re.match(r'^(#|\||```|>|- |\d+\. |---)', lines[i]):
        buf.append(lines[i].strip()); i += 1
    story.append(Paragraph(inline(' '.join(buf)), S['p']))

def footer(c, d):
    c.saveState(); c.setFont('MG', 7.5); c.setFillColor(MUTE)
    c.drawString(14 * mm, 8 * mm, TITLE)
    c.drawRightString(A4[0] - 14 * mm, 8 * mm, f'{d.page}')
    c.restoreState()

doc = BaseDocTemplate(dst, pagesize=A4, leftMargin=14 * mm, rightMargin=14 * mm, topMargin=14 * mm, bottomMargin=15 * mm,
                      title=TITLE, author='황유민')
doc.addPageTemplates([PageTemplate(id='a', frames=[Frame(14 * mm, 15 * mm, A4[0] - 28 * mm, A4[1] - 29 * mm, id='f', leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)], onPage=footer)])
doc.build(story)
print('ok')
