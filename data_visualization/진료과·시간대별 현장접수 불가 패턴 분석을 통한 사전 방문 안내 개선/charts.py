from pathlib import Path
from xml.sax.saxutils import escape
import json,hashlib,math
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate,Paragraph,Table,TableStyle,Spacer,PageBreak,Flowable
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib import colors
import pymupdf


R={}
pdfmetrics.registerFont(TTFont('MG','C:/Windows/Fonts/malgun.ttf'));pdfmetrics.registerFont(TTFont('MGB','C:/Windows/Fonts/malgunbd.ttf'))
pdfmetrics.registerFontFamily('MG',normal='MG',bold='MGB')
INK=colors.HexColor('#19374A');TEAL=colors.HexColor('#147E88');BLUE=colors.HexColor('#356AB0');ORANGE=colors.HexColor('#D77935');GRAY=colors.HexColor('#647785');PALE=colors.HexColor('#E8F1F4');LIGHT=colors.HexColor('#DCE6EB')
W=507
styles={
 'body':ParagraphStyle('body',fontName='MG',fontSize=9.3,leading=14.5,spaceAfter=7.5,wordWrap='CJK',textColor=INK),
 'h1':ParagraphStyle('h1',fontName='MGB',fontSize=17,leading=24,spaceAfter=12,wordWrap='CJK',textColor=INK),
 'h2':ParagraphStyle('h2',fontName='MGB',fontSize=11,leading=17,spaceBefore=8,spaceAfter=6,wordWrap='CJK',textColor=TEAL),
 'title':ParagraphStyle('title',fontName='MGB',fontSize=22,leading=32,spaceAfter=15,wordWrap='CJK',textColor=INK),
 'small':ParagraphStyle('small',fontName='MG',fontSize=8,leading=12,spaceAfter=7,wordWrap='CJK',textColor=GRAY),
 'cell':ParagraphStyle('cell',fontName='MG',fontSize=8.4,leading=12.5,wordWrap='CJK',textColor=INK),
 'compact':ParagraphStyle('compact',fontName='MG',fontSize=8.1,leading=12,wordWrap='CJK',textColor=INK),
}
S=[]
def P(t,k='body'):return Paragraph(t,styles[k])
def add(t,k='body'):S.append(P(t,k))
def table(head,rows,widths=None,compact=False):
 k='compact' if compact else 'cell'
 data=[[P(escape(str(v)),k) for v in head]]+[[P(escape(str(v)),k) for v in row] for row in rows]
 t=Table(data,colWidths=widths or [W/len(head)]*len(head),repeatRows=1,hAlign='LEFT')
 pad=5 if compact else 6
 t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),PALE),('VALIGN',(0,0),(-1,-1),'TOP'),('TOPPADDING',(0,0),(-1,-1),pad),('BOTTOMPADDING',(0,0),(-1,-1),pad),('LEFTPADDING',(0,0),(-1,-1),6),('RIGHTPADDING',(0,0),(-1,-1),6),('LINEBELOW',(0,0),(-1,0),.6,colors.HexColor('#A8C5D0')),('LINEBELOW',(0,1),(-1,-1),.25,LIGHT)]))
 S.extend([t,Spacer(1,7)])
def page(title):S.append(PageBreak());add(title,'h1')
def n(v):return f'{v:,.0f}'
def pct(v):return f'{v:.2f}%'
def pp(v):return f'{v:+.2f}'
def label(c,x,y,t,size=8,color=INK,align='left'):
 c.setFont('MG',size);c.setFillColor(color);getattr(c,{'left':'drawString','right':'drawRightString','center':'drawCentredString'}[align])(x,y,str(t))
def legend(c,items,x,y):
 for text,col in items:
  c.setFillColor(col);c.rect(x,y,7,7,stroke=0,fill=1);label(c,x+11,y,text,7.5);x+=max(70,len(text)*7+26)
class Chart(Flowable):
 def __init__(self,height,paint):Flowable.__init__(self);self.width=W;self.height=height;self.paint=paint
 def draw(self):self.paint(self.canv,W,self.height)


def heat_chart():
 priority={r['department_code']:i for i,r in enumerate(R['candidate'][:4])}
 departments=sorted({(r['department_code'],r['department_name']) for r in R['heat']},key=lambda x:(priority.get(x[0],99),x[0]))
 vals={(r['department_code'],r['arrival_hour']):r for r in R['heat']};hours=list(range(8,15))
 def color(v):
  t=min(1,max(0,v/60));return colors.Color(.95-.85*t,.98-.49*t,.99-.44*t)
 def paint(c,w,h):
  left=85;bottom=42;top=h-24;cw=(w-left-4)/7;ch=(top-bottom)/12
  for j,hr in enumerate(hours):label(c,left+(j+.5)*cw,top+10,f'{hr}시',8,INK,'center')
  for i,(code,name) in enumerate(departments):
   y=top-(i+1)*ch;label(c,left-7,y+ch*.5-3,name,8,INK,'right')
   for j,hr in enumerate(hours):
    r=vals.get((code,hr));v=r['rate'] if r else None
    c.setFillColor(color(v) if v is not None else colors.HexColor('#D8DDE1'));c.rect(left+j*cw,y,cw-1,ch-1,fill=1,stroke=0)
    label(c,left+(j+.5)*cw,y+ch*.5-3,f'{v:.1f}%' if v is not None else 'NA',8,colors.white if v is not None and v>38 else INK,'center')
  xx=left+20;yy=13;ww=230
  for j in range(120):c.setFillColor(color(j/119*60));c.rect(xx+j*ww/120,yy,ww/120+1,8,stroke=0,fill=1)
  for v in [0,15,30,45,60]:label(c,xx+ww*v/60,yy-10,str(v),7,GRAY,'center')
  label(c,xx+ww+12,yy,'접수불가율(%)',7,GRAY)
 return Chart(325,paint)

def trend_chart():
 top4=R['candidate'][:4]
 def paint(c,w,h):
  for idx,r in enumerate(top4):
   x0=(idx%2)*(w/2);y0=(1-idx//2)*(h/2);left=x0+30;right=x0+w/2-10;bot=y0+30;top=y0+h/2-38
   label(c,x0+8,y0+h/2-10,f"{r['department_name']} {r['arrival_hour']:02d}시대",9)
   label(c,x0+8,y0+h/2-23,f"36/36 months | min n={r['min_monthly_n']}",7,GRAY)
   for v in [0,30,60]:
    y=bot+(top-bot)*v/60;c.setStrokeColor(LIGHT);c.line(left,y,right,y);label(c,left-4,y-3,v,7,GRAY,'right')
   rows=sorted([x for x in R['mh'] if x['department_code']==r['department_code'] and x['arrival_hour']==r['arrival_hour']],key=lambda x:x['arrival_month'])
   for key,col in [('rate',ORANGE),('reference_rate',BLUE)]:
    c.setStrokeColor(col);c.setLineWidth(1.2);p=c.beginPath()
    for j,v in enumerate(rows):
     x=left+(right-left)*j/35;y=bot+(top-bot)*v[key]/60
     (p.moveTo if j==0 else p.lineTo)(x,y)
    c.drawPath(p)
   for j in [0,12,24,35]:label(c,left+(right-left)*j/35,bot-12,rows[j]['arrival_month'][2:],6.5,GRAY,'center')
  legend(c,[('구간 접수불가율',ORANGE),('같은 월·진료과 전체',BLUE)],80,0)
 return Chart(285,paint)

def rate_chart():
 overall=100*R['total']['rejected_count']/R['total']['walk_in_count']
 rows=sorted(R['dept'],key=lambda r:r['rate'],reverse=True)
 def paint(c,w,h):
  left=90;right=385;top=h-31;step=17
  label(c,left,top+20,'접수불가율(%)',8)
  label(c,485,top+20,'불가 / 현장(건)',8,INK,'right')
  for v in [0,10,20,30]:
   x=left+(right-left)*v/30;c.setStrokeColor(LIGHT);c.line(x,top-12*step,x,top+4);label(c,x,top+7,v,7,GRAY,'center')
  for j,r in enumerate(rows):
   y=top-j*step-11;label(c,left-7,y+2,r['department_name'],8,INK,'right');c.setFillColor(TEAL);c.rect(left,y,(right-left)*r['rate']/30,10,fill=1,stroke=0)
   label(c,left+(right-left)*r['rate']/30+4,y+1,f"{r['rate']:.2f}",7.5)
   label(c,500,y+1,f"{n(r['rejected_count'])} / {n(r['walk_in_count'])}",7.5,INK,'right')
  c.setStrokeColor(ORANGE);c.setDash(2,2);x=left+(right-left)*overall/30;c.line(x,top-12*step,x,top+4);c.setDash()
  label(c,left,4,f'주황 점선: 전체 {overall:.2f}%',8,ORANGE)
 return Chart(270,paint)
