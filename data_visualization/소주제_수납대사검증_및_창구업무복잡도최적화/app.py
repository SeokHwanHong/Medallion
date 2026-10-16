"""[백선영] 목적: 병원 수납 기록 점검·가정 비교. 입력: 최종 MySQL 로컬 Parquet/공식통계 JSON. 출력: 동적 화면·다운로드."""
from pathlib import Path
import json
import pandas as pd
import numpy as np
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from analysis import summarize, method_table, monthly_table, select_targets
from export_utils import csv_bytes


# ===== 시나리오 계산: 이 파일에 포함 =====
"""[백선영] 실제 캐시 거래와 분리한 결제·환불 시점 가정 비교.

금액·거래 종류·PK·원결제 연결을 보존하고 메모리의 거래 시각만 변경한다.
최종 청구 변경 이력이 없으므로 과거 net_charge 대사/미수금은 계산하지 않는다.
최종 결제·환불 내역을 알고 있다는 사후 가정으로 시점별 기록 잔액을 비교한다.
"""
from dataclasses import dataclass
import numpy as np
import pandas as pd


@dataclass(frozen=True)
class Settings:
    first_delay_percent: int = 0
    first_delay_days: int = 0
    balance_extra_days: int = 0
    refund_extra_days: int = 0
    seed: int = 42

    def validate(self):
        if not 0 <= self.first_delay_percent <= 100:
            raise ValueError('첫 결제 추가 지연 비율은 0~100이어야 합니다.')
        if any(not 0 <= v <= 90 for v in (
                self.first_delay_days, self.balance_extra_days, self.refund_extra_days)):
            raise ValueError('추가 지연은 0~90일이어야 합니다.')


PRESETS = {
    '기준 기록 그대로': Settings(),
    '첫 결제 지연 가정': Settings(30, 7, 0, 0),
    '분할 잔액 지연 가정': Settings(0, 0, 14, 0),
    '환불 처리 지연 가정': Settings(0, 0, 0, 14),
    '결제·환불 복합 지연 가정': Settings(30, 7, 14, 14),
    '대응 가정: 추가 지연 축소': Settings(30, 1, 3, 2),
}


def prepare_population(f, p):
    """선택 진료 집단의 모든 거래를 사용한다. 거래월 필터로 후속 거래를 자르지 않는다."""
    if not f.encounter_id.is_unique or not p.payment_id.is_unique:
        raise ValueError('진료 또는 거래 PK가 중복되어 시나리오를 중단했습니다.')
    tx = p[p.encounter_id.isin(f.encounter_id)].copy()
    tx['transacted_at'] = pd.to_datetime(tx.transacted_at, errors='coerce')
    tx['amount'] = pd.to_numeric(tx.amount, errors='coerce')
    invalid = (~tx.transaction_type.isin(['PAYMENT', 'REFUND']) |
               tx.amount.isna() | tx.amount.le(0) | tx.amount.mod(1).ne(0) |
               tx.transacted_at.isna())
    bad_ids = set(tx.loc[invalid, 'encounter_id'])
    # 환불의 원거래를 독립 확인한다. 기존 hold 플래그만 신뢰하지 않는다.
    original = tx[['payment_id', 'encounter_id', 'transaction_type', 'transacted_at', 'amount']].rename(
        columns={'payment_id': 'original_id', 'encounter_id': 'original_encounter',
                 'transaction_type': 'original_type', 'transacted_at': 'original_at',
                 'amount': 'original_amount'})
    refunds = tx[tx.transaction_type.eq('REFUND')].merge(
        original, left_on='original_payment_id', right_on='original_id', how='left', validate='many_to_one')
    if not refunds.empty:
        valid_link = (refunds.original_id.notna() & refunds.original_type.eq('PAYMENT') &
                      refunds.encounter_id.eq(refunds.original_encounter) &
                      refunds.transacted_at.ge(refunds.original_at))
        total = refunds.groupby('original_payment_id', dropna=False).amount.transform('sum')
        bad_ids.update(refunds.loc[~valid_link | total.gt(refunds.original_amount), 'encounter_id'])
        # 서로 다른 진료를 가리키는 환불이면 양쪽 모두 비교 대상에서 제외한다.
        bad_ids.update(refunds.loc[~valid_link, 'original_encounter'].dropna())
    tx['paid'] = tx.amount.where(tx.transaction_type.eq('PAYMENT'), 0)
    tx['refunded'] = tx.amount.where(tx.transaction_type.eq('REFUND'), 0)
    totals = tx.groupby('encounter_id')[['paid', 'refunded']].sum()
    x = f.copy()
    for col in ['started_at', 'ended_at']:
        x[col] = pd.to_datetime(x[col], errors='coerce')
    paid = x.encounter_id.map(totals.paid).fillna(0)
    refunded = x.encounter_id.map(totals.refunded).fillna(0)
    usable = (x.completed.fillna(False) & ~x.hold.fillna(True) &
              x.ended_at.gt(x.started_at) & x.gross_charge.gt(0) &
              x.authorized_refund.ge(0) & x.authorized_refund.le(x.gross_charge) &
              x.net_charge.eq(x.gross_charge - x.authorized_refund) &
              paid.eq(x.gross_charge) & refunded.eq(x.authorized_refund) &
              ~x.encounter_id.isin(bad_ids))
    population = x[usable].copy().reset_index(drop=True)
    ledger = tx[tx.encounter_id.isin(population.encounter_id)].copy().reset_index(drop=True)
    report = {'selected_encounters': len(x), 'eligible_encounters': len(population),
              'excluded_encounters': int((~usable).sum()), 'transactions': len(ledger)}
    return population, ledger, report

    st.caption('국내 공식 통계 · 대주제: 병원 진료 및 수납 시스템 최적화')
    src=json.loads((ROOT/'official_sources.json').read_text(encoding='utf-8'))
    by={s['id']:s for s in src['sources']}
    cols=st.columns(3)
    for col,key in zip(cols,['coverage','aging','doctors']):
        v=by[key]
        with col:
            st.metric(v['indicator'],f"{v['value']:,.1f} {v['unit']}")
            st.caption(f"기준: {v['year']} · {v['agency']}")
            st.caption(v['definition'])
            st.link_button('공식 출처',v['url'])
    insured=by['insured']
    st.write(f"건강보험 적용 대상자: {insured['value']:,}천 명({insured['year']}). 이는 의료급여를 포함한 총인구나 적용률이 아닙니다. [국민건강보험공단 원표]({insured['url']})")
    st.write('의료보장이 넓게 적용되어도 법정·비급여 본인부담은 남을 수 있습니다. 고령화로 미수납 증가나 개인의 지불 능력을 추정하지 않습니다. 전국 의사 수만으로 특정 병원·진료과의 인력 부족도 확정하지 않습니다.')
    left,right=st.columns(2)
    with left:
        d=pd.DataFrame({'연도':by['coverage']['trend'].keys(),'보장률(%)':by['coverage']['trend'].values()})
        chart(px.line(d,x='연도',y='보장률(%)',markers=True,title='건강보험 보장률 추이 · 2019~2024').update_yaxes(range=[0,100]),'official_coverage')
        st.caption('출처: e-나라지표, 보건복지부·국민건강보험공단. 단위 %, 정의는 위 카드 참조.')
    with right:
        d=pd.DataFrame({'지역':by['aging']['regional'].keys(),'65세 이상 비중(%)':by['aging']['regional'].values()})
        chart(px.bar(d,x='지역',y='65세 이상 비중(%)',title='지역별 고령인구 비중 · 2025 추계'),'official_aging')
        st.caption('출처: 통계청 2025 고령자 통계. 65세 이상 추계인구/전체 추계인구, %.')
    st.info('의료환경 변화 속에서 병원 운영을 살펴보기 위해, 본 프로젝트는 합성데이터의 진료·결제·환불 기록을 분석하고 재정 관리와 수납 업무의 개선 방향을 탐색합니다.')
    st.caption(src['limits'])
    with st.expander('출처·정의·제외 항목'):
        for v in src['sources']:
            st.write(f"**{v['indicator']} · {v['year']} · {v['unit']}** — {v['definition']} / {v['agency']} / [출처]({v['url']})")
            if 'year_definition_url' in v:st.write(f"[기준연도·한의사 포함 정의 확인]({v['year_definition_url']})")
        st.write('\n\n'.join(src['excluded']))
    st.download_button('통계·출처 목록 다운로드',(ROOT/'official_sources.json').read_bytes(),'국내공식통계_출처.json','application/json')
    def go_to_overview():
        st.session_state['page']='① 현황'
    st.button('합성데이터 현황으로 이동',on_click=go_to_overview)

if not (ROOT/'summary.json').exists():
    st.error('최종 MySQL 추출·분석 결과가 없습니다. secure_snapshot.py → analysis.py를 실행해 주세요.');st.stop()
summary=json.loads((ROOT/'summary.json').read_text(encoding='utf-8'))
f,p=load_data((ROOT/'data/encounters.parquet').stat().st_mtime_ns,
              (ROOT/'data/payments.parquet').stat().st_mtime_ns)
st.sidebar.title('수납 기록 분석')
st.sidebar.button('초기화',on_click=reset,width='stretch')
page=st.sidebar.radio('화면',['국내 의료환경과 분석 배경','① 현황','② 흐름','③ 비교','④ 시나리오 실험 및 TO-BE'],key='page')
if page=='국내 의료환경과 분석 배경':
    official_page();st.stop()

minimum=min(f.started_at.min(),p.transacted_at.min()).date();maximum=max(f.ended_at.max(),p.transacted_at.max()).date()
dates=st.sidebar.date_input('기간',value=(minimum,maximum),min_value=minimum,max_value=maximum,key='period')
hospitals=st.sidebar.multiselect('병원',sorted(f.hospital_id.unique()),key='hospitals',help='비워두면 전체. 병원 ID와 이름은 결과표에서 확인합니다.')
departments=st.sidebar.multiselect('진료과',sorted(f.department_name.unique()),key='departments',help='비워두면 전체')
st.sidebar.caption('기준 분석: 최종 DB 스냅샷 · 가정 비교는 ④ 시나리오 화면에서 선택합니다.')
if len(dates)!=2:st.info('시작일과 종료일을 선택해 주세요.');st.stop()
start,end=map(pd.Timestamp,dates);exclusive_end=end+pd.Timedelta(days=1)
fm=f.started_at.ge(start)&f.started_at.lt(exclusive_end)
pm=p.transacted_at.ge(start)&p.transacted_at.lt(exclusive_end)
if hospitals:fm &= f.hospital_id.isin(hospitals);pm &= p.hospital_id.isin(hospitals)
if departments:fm &= f.department_name.isin(departments);pm &= p.department_name.isin(departments)
sf=f.loc[fm];sp=p.loc[pm]
st.title('진료 후 결제·환불 패턴 분석')
st.caption(f"합성데이터 분석 · [백선영] · 최종 MySQL team3_medallion · 스냅샷 {summary['snapshot']['snapshot_time']} (서버 표시)")
st.write(f"현재 선택: **{start.date()}~{end.date()} · 병원 {', '.join(hospitals) if hospitals else '전체'} · 진료과 {', '.join(departments) if departments else '전체'} · 기준 데이터: 최종 스냅샷**")
st.caption('진료 지표의 기간은 진료 시작일, 거래 지표의 기간은 거래일입니다. 진료 대사는 해당 진료의 최종 스냅샷까지 모든 연결 거래를 합산합니다. 선택 기간 안의 거래만으로 진료 차액을 만들지 않습니다.')
a,b,c,d=st.columns(4)
a.metric('선택 진료 / 완료',f'{len(sf):,} / {sf.completed.sum():,}')
b.metric('판단 보류 / 비교 가능',f'{sf.hold.sum():,} / {(~sf.hold).sum():,}')
c.metric('미분류 진료',f'{(sf.hospital_id.eq("미분류")|sf.department_code.eq("미분류")).sum():,}')
d.metric('선택 거래 / 미연결',f'{len(sp):,} / {sp.hospital_id.eq("미연결").sum():,}')
st.caption('원천 기록 범위: '+summary['date_min']+' ~ '+summary['date_max']+' · 현재 최종 보존 집단의 대사이며 정제·제외 이전 전체의 업무 성과가 아닙니다.')
if sf.empty and sp.empty:st.warning('선택 조건에 해당하는 결과가 없습니다. 조건을 넓히거나 초기화하세요.')

if page=='① 현황':
    st.subheader('결제수단 → 거래월별 결제·환불')
    mt=method_table(sp);months=monthly_table(sp)
    st.caption('수단별 분모: 같은 거래종류 전체 거래 건수·금액. 이 분포만으로 효율이나 선호를 판단하지 않습니다.')
    if not mt.empty:chart(px.bar(mt[mt.payment_method.ne('전체 합계')],x='payment_method',y='amount',color='transaction_type',barmode='group',title='수단별 거래금액 · 원'),'method')
    table(mt,'S02_선택결제수단')
    if not months.empty:
        chart(px.bar(months,x='transaction_month',y=['paid','refunded'],barmode='group',title='거래 발생월별 결제·환불 · 원'),'monthly')
        chart(px.line(months,x='transaction_month',y='refund_payment_ratio',markers=True,title='환불금액 / 같은 거래월 결제금액 · %'),'monthly_ratio')
    table(months,'S03_선택거래월')

elif page=='② 흐름':
    st.subheader('수납 기록 퍼널 → 분할 결제 → 환불')
    co=sf[sf.completed];ass=co[~co.hold]
    stages=['진료 완료','결제 기록 발생','비교 가능·결제 발생·금액 일치']
    counts=[len(co),int(co.payment_count.gt(0).sum()),int((~co.hold&co.payment_count.gt(0)&co.gap.eq(0)).sum())]
    comparable=[len(ass),int(ass.payment_count.gt(0).sum()),int((ass.payment_count.gt(0)&ass.gap.eq(0)).sum())]
    funnel=pd.DataFrame({'단계':stages,'전체집단_건수':counts,'전체완료대비':[percent(v,len(co)) for v in counts],'비교가능집단_건수':comparable,'비교가능완료대비':[percent(v,len(ass)) for v in comparable]})
    chart(go.Figure(go.Funnel(y=stages,x=counts,textinfo='value+percent initial')).update_layout(title='기록 기반 퍼널 · 임상 성공·승인·실제 납부 성공 퍼널이 아님'),'funnel')
    table(funnel,'S06_선택퍼널')
    st.caption(f'전체 완료 {len(co):,}건 / 판단 보류 {co.hold.sum():,}건 / 0원 순청구 {co.net_charge.eq(0).sum():,}건. 완료는 시각 존재·순서 기준입니다.')
    splits=summarize(sf,['split_group','method_bundle']);table(splits,'S04_선택분할결제')
    st.write('결제횟수 구간 전체: '+ ' · '.join(f'{name} {int(sf.split_group.eq(name).sum()):,}진료' for name in ['0회','1회','2회','3회 이상']))
    st.caption('집단별 일치율 분모=비교가능 진료, 보류·분할·환불 비율 분모=해당 집단 전체. 여러 PAYMENT는 진료별로 합산하며 중복 오류로 단정하지 않습니다.')
    if not splits.empty:chart(px.bar(splits,x='split_group',y='encounters',color='method_bundle',title='결제 횟수·수단 조합별 진료 수'),'split')
    refund_n=int(sf.refund_count.gt(0).sum())
    st.write(f'환불 발생 진료 **{refund_n:,}/{len(sf):,}건 ({percent(refund_n,len(sf))})**, 기록 환불액 **{sf.refunded.sum():,.0f}원**, 승인 환불액 **{sf.authorized_refund.sum():,.0f}원**, 차이 **{sf.refunded.sum()-sf.authorized_refund.sum():,.0f}원**')
    rf=pd.read_parquet(ROOT/'data/refund_links.parquet');rf=rf[rf.encounter_id.isin(sf.encounter_id)]
    st.write(f'원결제 연결 부적합 {int((~rf.link_valid).sum()):,}건 / 누적 한도 초과 환불 행 {int(rf.over_limit.sum()):,}건 / 전체 환불 행 {len(rf):,}건')
    table(rf[['payment_id','encounter_id','original_payment_id','amount','original_amount','cumulative_refund','link_valid','over_limit']],'S05_선택원결제추적')

elif page=='③ 비교':
    st.subheader('진료월 코호트 → 병원·진료과 비교')
    cohort=summarize(sf,'treatment_month');table(cohort,'S07_선택진료월')
    if not cohort.empty:
        chart(px.line(cohort,x='treatment_month',y=['match_rate','hold_rate'],markers=True,title='진료월별 최종 금액 일치·보류 비율 · %').update_yaxes(range=[0,100]),'cohort')
        chart(px.line(cohort,x='treatment_month',y=['refund_rate','split_rate'],markers=True,title='진료월별 환불·분할 결제 발생률 · %').update_yaxes(rangemode='tozero'),'cohort_patterns')
        st.caption('금액 일치율과 업무 패턴 비율을 별도 그래프로 표시합니다. 차이가 작으면 작은 차이로 설명하며 통계적·운영상 의미를 자동으로 부여하지 않습니다.')
        chart(px.bar(cohort,x='treatment_month',y=['shortfall','excess','absolute_gap'],barmode='group',title='비교가능 진료의 부족·초과·절대 차액 · 원'),'cohort_gaps')
    groups=summarize(sf,['hospital_id','hospital_name','department_code','department_name']).sort_values(['absolute_gap','hold','missing','encounters'],ascending=False)
    st.caption('기록 차이·보류·부재를 먼저 보고 규모를 함께 비교합니다. 모두 0이면 수납 문제에 따른 점검 우선순위 차이는 확인되지 않습니다. 환불·분할 건수는 업무 확인 규모이며 문제 발생률이 아닙니다.')
    table(groups,'S08_선택병원진료과')
    if not groups.empty:
        top=groups.head(20).copy();top['병원·진료과']=top.hospital_id+' / '+top.department_name
        chart(px.bar(top,x='병원·진료과',y='encounters',color='refund_rate',title='규모 상위 표시 · 색=환불 발생률(%)'),'hospital')

else:
    render_scenarios(sf, p, chart, table)
    st.subheader('TO-BE · 설명과 흐름도')
    st.markdown('**감염병 대응 확장**: 향후 유행 전·중·후의 비교 가능한 수요·진료·거래 자료와 관찰기간을 확보하여 패턴 변화와 비상시 대응 방향을 살펴봅니다. 현재 자료로 팬데믹 영향을 분석하지 않았습니다.')
    st.graphviz_chart('digraph { rankdir=LR; "비교 가능한 유행 전·중·후 자료 확보" -> "진료 수요·결제·환불 패턴 비교" -> "비상시 수납·인력 대응 검토"; }')
    st.markdown('**환자 의료비 지원 연계**: 기록 차이만으로 경제적 어려움을 추정하거나 지원 대상·자격을 판정하지 않습니다. 병원 운영 지원과 환자 의료비 지원은 별도 목적과 절차입니다.')
    st.graphviz_chart('digraph { rankdir=LR; "기록 대사" -> "실제 납부 상태 확인" -> "상담 안내·의향 확인" -> "동의" -> "최소 정보 확인" -> "담당자 자격 검토" -> "적합한 제도 안내·지원 연계" -> "결정·입금·잔액 추적"; }')
    st.caption('향후 흐름만 제시합니다. 오늘은 개인정보 입력·실제 신청·자격 판정을 구현하지 않습니다. 자료 없는 지원 전환율·효과를 만들지 않습니다.')

with st.expander('계산·분모·한계'):
    st.write('순수납 기록액 = PAYMENT 합 − REFUND 합. 차액 = 순수납 기록액 − net_charge. 양수=초과 기록, 음수=부족 기록. 서비스와 거래를 각각 진료별로 선집계한 뒤 연결했습니다. 금액 차이는 보류 사유가 아닙니다.')
    st.write('판단 보류: 완료·청구·거래·서비스 근거 불완전 또는 환불 연결·누적한도 부적합. 병원·진료과 미분류는 금액 대사의 보류 사유로 삼지 않습니다. 비교가능 집단은 현재 최종 보존 기록 범위입니다.')
