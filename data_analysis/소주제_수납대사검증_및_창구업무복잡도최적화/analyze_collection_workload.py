"""목적: 수정 합성자료와 최종 캐시의 오프라인 주제 분석. 입력: 보존된 CSV/Parquet. 출력: SQL, 결과, Gold, 발표 차트. DB 접속 없음."""
from pathlib import Path
import hashlib, json, sqlite3
import pandas as pd
import plotly.express as px
import plotly.io as pio

ROOT = Path(__file__).resolve().parent
SRC = ROOT.parent / 'synthetic_supplement_corrected_20261015_163609'
FINAL = ROOT.parent / 'collection_dashboard_20261015'
for sub in ['sql', 'results', 'charts']:
    (ROOT/sub).mkdir(exist_ok=True)
manifest = json.loads((SRC/'manifest.json').read_text(encoding='utf-8'))
checks = {}
con = sqlite3.connect(':memory:')
tables = {}
for name, expected in manifest['output_sha256'].items():
    path = SRC/'fyi'/f'{name}.csv'
    checks[f'hash_{name}'] = hashlib.sha256(path.read_bytes()).hexdigest() == expected
    assert checks[f'hash_{name}'], path
    tables[name] = pd.read_csv(path)
    tables[name].to_sql(name, con, index=False)
f = pd.read_parquet(FINAL/'data/encounters.parquet')
p = pd.read_parquet(FINAL/'data/payments.parquet')
f.to_sql('final_encounters', con, index=False)
p[['payment_id','encounter_id']].to_sql('final_payments', con, index=False)
con.execute('CREATE INDEX local_payment_key ON final_payments(payment_id,encounter_id)')
# 인덱스는 로컬 SQLite 메모리 전용이다. MySQL에는 접속하지 않는다.
queries = {}
def add(key, question, grain, denominator, interpretation, connection, sql):
    head = f'-- 목적: {question}\n-- 입력: 로컬 캐시 및 수정 합성자료; 출력: {key} 결과\n-- 질문: {question}\n-- 한 행의 의미: {grain}\n-- 모집단·분모: {denominator}\n-- 결과 해석: {interpretation}\n-- 소주제와 연결: {connection}\n-- 실행: SQLite 로컬 메모리. MySQL 8 호환 SELECT 구문이나 현재 MySQL 실행 미검증.\n-- final_*는 로컬 캐시 별칭이며 실제 DB 테이블명이 아님. DB 생성·적재 지시가 아님.\n'
    (ROOT/'sql'/f'{key}.sql').write_text(head+sql.strip()+';\n',encoding='utf-8')
    result=pd.read_sql_query(sql,con)
    result.to_csv(ROOT/'results'/f'{key}.csv',index=False,encoding='utf-8-sig')
    queries[key]=result
    return result

q1=add('S01_final_finance','최종 기록에서 차이와 합산 확인 규모는?', '전체 완료 진료 1행','완료 진료; 비교 가능 집단은 hold=0','차이는 실제 미수금이 아니며 0이면 그대로 공개','기존 재정 대사 결과를 보존', '''
SELECT COUNT(*) encounters, SUM(CASE WHEN hold=0 THEN 1 ELSE 0 END) assessable,
SUM(CASE WHEN hold=0 AND gap=0 THEN 1 ELSE 0 END) matched,
SUM(CASE WHEN hold=0 AND gap<>0 THEN 1 ELSE 0 END) difference,
SUM(CASE WHEN payment_count=0 THEN 1 ELSE 0 END) missing_payment,
SUM(hold) hold_count, SUM(CASE WHEN payment_count>=2 THEN 1 ELSE 0 END) split_count,
SUM(CASE WHEN refund_count>0 THEN 1 ELSE 0 END) refund_count,
SUM(paid) paid, SUM(refunded) refunded, SUM(recorded_net) recorded_net,
SUM(CASE WHEN hold=0 THEN ABS(gap) ELSE 0 END) absolute_gap
FROM final_encounters WHERE completed=1''')
q2=add('S02_workload_scenario','수납 확인 절차의 복잡화 가정에 따라 작업량은 어떻게 변하는가?', '시나리오별 작업 유형','시나리오마다 같은 결제 1749건; 시나리오 합산 금지','생성된 task-minutes이며 실제 노동시간이나 대기시간 아님','재확인 절차 설계의 민감도', '''
SELECT scenario_id, task_type, COUNT(*) tasks, COUNT(DISTINCT payment_id) payments,
SUM(work_minutes) task_minutes, AVG(work_minutes) minutes_per_task
FROM ext_collection_worklogs WHERE scenario_id IN ('BASE','COLLECTION_COMPLEX')
GROUP BY scenario_id,task_type ORDER BY scenario_id,task_type''')
q3=add('S03_historical_evidence','수정본 생성 당시 대사 근거별 확인 대상은?', 'BASE 대사 판정별 1행','BASE RECONCILE 작업만; CHECK 미판정은 보류로 세지 않음','과거 로컬 입력 기준으로 현재 최종 DB 판정과 다름','금액 차이와 근거 부족을 다른 경로로 점검', '''
SELECT reconciliation_result,COUNT(*) payment_count,SUM(work_minutes) reconcile_task_minutes,
100.0*COUNT(*)/(SELECT COUNT(*) FROM ext_collection_worklogs WHERE scenario_id='BASE' AND task_type='RECONCILE') percent
FROM ext_collection_worklogs WHERE scenario_id='BASE' AND task_type='RECONCILE'
GROUP BY reconciliation_result''')
q4=add('S04_final_link_coverage','수정본 결제가 최종 캐시에 얼마나 남아 있는가?', '과거 판정×최종 키 연결 여부','BASE RECONCILE 1749건; payment_id와 encounter_id 동시 일치','키 일치가 옛 판정의 현재 유효성을 뜻하지 않음; 미연결 원인은 확정 불가','서로 다른 기준의 자료 혼합 방지', '''
SELECT w.reconciliation_result,
CASE WHEN p.payment_id IS NULL THEN 'NOT_LINKED' ELSE 'LINKED' END linkage,
COUNT(*) payments
FROM ext_collection_worklogs w LEFT JOIN final_payments p
ON w.payment_id=p.payment_id AND w.encounter_id=p.encounter_id
WHERE w.scenario_id='BASE' AND w.task_type='RECONCILE'
GROUP BY w.reconciliation_result,CASE WHEN p.payment_id IS NULL THEN 'NOT_LINKED' ELSE 'LINKED' END''')
q5=add('S05_booking_demand','추가 예약 수요 가정에서 제안가능 비율과 대기 발생은?', '시나리오×요청 판단','활성 요청만; WITHDRAWN도 활성 분모에 포함; 비활성 비교행 제외','OFFERABLE은 가정상 제안가능이며 예약 확정 아님','확장 주제: 수요 대응 절차; 재정 차이 원인으로 연결하지 않음', '''
WITH a AS (SELECT * FROM ext_booking_requests WHERE is_active='Y' AND scenario_id IN ('BASE','DEMAND_UP')),
d AS (SELECT scenario_id,COUNT(*) denominator FROM a GROUP BY scenario_id)
SELECT a.scenario_id,a.decision,COUNT(*) requests,d.denominator,
100.0*COUNT(*)/d.denominator percent FROM a JOIN d ON a.scenario_id=d.scenario_id
GROUP BY a.scenario_id,a.decision,d.denominator''')
q6=add('S06_booking_hospital','병원별 추가 요청의 제안가능 비율은?', '시나리오×병원','각 병원의 활성 요청','표본 12개 병원; 수요 증가 가정이며 실제 병원 병목 증거 아님','규모와 비율을 함께 비교하는 확장 분석', '''
SELECT scenario_id,hospital_id,COUNT(*) active_requests,
SUM(CASE WHEN decision='OFFERABLE' THEN 1 ELSE 0 END) offerable,
SUM(CASE WHEN decision='WAITLIST' THEN 1 ELSE 0 END) waitlist,
100.0*SUM(CASE WHEN decision='OFFERABLE' THEN 1 ELSE 0 END)/COUNT(*) offerable_percent
FROM ext_booking_requests WHERE is_active='Y' AND scenario_id IN ('BASE','DEMAND_UP')
GROUP BY scenario_id,hospital_id''')
q7=add('S07_service_proxy','서비스 업무량 가정은 무엇을 비교할 수 있는가?', '서비스 코드×시나리오','가격 버전별 값을 먼저 코드 단위 평균; 병원 총량으로 합산하지 않음','진료시간 배분 기반 대용값; 실측 서비스 시간·난이도 아님','확장 민감도 주제; 25% 증가는 설계값', '''
SELECT scenario_id,service_code,COUNT(*) price_versions,
AVG(assumed_standard_minutes) proxy_minutes,AVG(assumed_workload_weight) proxy_weight
FROM ext_service_workload WHERE scenario_id IN ('BASE','WORKLOAD_UP')
GROUP BY scenario_id,service_code''')
q8=add('S08_final_hospital','최종 병원별 분할결제·환불의 합산 확인 규모는?', '병원별 1행','해당 병원 완료 진료 전체','건수는 처리 규모; 비율 차이가 작으면 성과 우열로 표현하지 않음','점검 우선순위는 오류 발생 순위가 아니라 합산 확인 규모', '''
SELECT hospital_id,hospital_name,COUNT(*) encounters,
SUM(CASE WHEN payment_count>=2 THEN 1 ELSE 0 END) split_count,
100.0*SUM(CASE WHEN payment_count>=2 THEN 1 ELSE 0 END)/COUNT(*) split_percent,
SUM(CASE WHEN refund_count>0 THEN 1 ELSE 0 END) refund_count,
100.0*SUM(CASE WHEN refund_count>0 THEN 1 ELSE 0 END)/COUNT(*) refund_percent,
SUM(CASE WHEN hold=0 AND gap<>0 THEN 1 ELSE 0 END) difference_count,SUM(hold) hold_count
FROM final_encounters WHERE completed=1 GROUP BY hospital_id,hospital_name ORDER BY split_count DESC''')

w=tables['ext_collection_worklogs']
base=w.query("scenario_id=='BASE' and task_type=='RECONCILE'")
checks.update(final_encounter_key_unique=not f.encounter_id.duplicated().any(),final_payment_key_unique=not p.payment_id.duplicated().any(),base_reconcile_key_unique=not base.payment_id.duplicated().any(),worklog_pk_unique=not w.worklog_id.duplicated().any(),coverage_partition=int(q4.payments.sum())==len(base),status_partition=int(q3.payment_count.sum())==len(base),base_task_sum=float(q2.query("scenario_id=='BASE'").task_minutes.sum())==20937,complex_task_sum=float(q2.query("scenario_id=='COLLECTION_COMPLEX'").task_minutes.sum())==46920)
for scenario,g in w.groupby('scenario_id'):
    checks['same_payment_cohort_'+scenario]=set(zip(g.payment_id,g.encounter_id))==set(zip(base.payment_id,base.encounter_id))
assert all(checks.values()),checks
linked=int(q4.query("linkage=='LINKED'").payments.sum())
figures=[]
def chart(name,fig,footnote):
    labels={'BASE':'기본 가정','COLLECTION_COMPLEX':'수납 복잡화 가정','DEMAND_UP':'수요 증가 가정','CHECK':'확인','RECONCILE':'대사','RECHECK':'재확인','HOLD_INCOMPLETE_OR_INVALID':'불완전 근거 보류','HOLD_INPUT_BASIS_DIFFERENCE':'입력 기준 차이 보류','OBSERVED_DIFFERENCE':'금액 차이','OBSERVED_MATCH':'일치','LINKED':'최종 캐시 연결','NOT_LINKED':'최종 캐시 미연결','OFFERABLE':'제안가능','WITHDRAWN':'철회','split_count':'분할결제 진료','refund_count':'환불 진료'}
    for trace in fig.data:
        if trace.x is not None:
            trace.x=[labels.get(str(x),x) for x in trace.x]
        trace.name=labels.get(trace.name,trace.name)
    fig.update_xaxes(tickangle=0)
    fig.update_layout(template='plotly_white',font=dict(family='Malgun Gothic, Arial',size=20),width=1280,height=720,margin=dict(b=130,t=100),legend_title_text='')
    fig.add_annotation(text=footnote,x=0,y=-.23,xref='paper',yref='paper',showarrow=False,xanchor='left',font=dict(size=14))
    path=ROOT/'charts'/f'{name}.html'
    fig.write_html(path,include_plotlyjs=True)
    figures.append((name,path))
chart('01_workload',px.bar(q2,x='scenario_id',y='task_minutes',color='task_type',barmode='stack',title='수납 확인 작업량: 기본 가정과 복잡화 가정',labels={'task_minutes':'합성 작업분(task-minutes)','scenario_id':'가정'}),'수정 합성자료 · 동일 결제 1,749건 · 실제 인력 소요시간 및 업무 증가의 관측값 아님')
chart('02_evidence',px.bar(q3,x='reconciliation_result',y='payment_count',text='payment_count',title='수정본 생성 당시의 대사 근거 분류',labels={'payment_count':'결제 건수','reconciliation_result':'과거 로컬 입력 기준 판정'}),'BASE RECONCILE 1,749건 · 최종 DB의 현재 오류·미수금으로 해석 금지')
chart('03_linkage',px.bar(q4,x='reconciliation_result',y='payments',color='linkage',title='과거 판정과 최종 캐시 연결 범위',labels={'payments':'결제 건수','reconciliation_result':'과거 판정'}),'payment_id + encounter_id 일치 · 미연결을 미납 또는 오류로 분류하지 않음')
chart('04_booking',px.bar(q5,x='scenario_id',y='requests',color='decision',title='추가 예약 수요 가정: 제안가능·철회 요청',labels={'requests':'활성 요청 건수','scenario_id':'가정'}),'BASE 1,944건 / DEMAND_UP 3,888건 · WAITLIST 0건 · 예약 확정 또는 병목 검출 아님')
top=q8.head(12).copy()
chart('05_finance_volume',px.bar(top,x='hospital_id',y=['split_count','refund_count'],barmode='group',title='분할결제 건수 상위 12개 병원의 합산 확인 규모',labels={'value':'진료 건수','hospital_id':'병원','variable':'기록 유형'}),'최종 캐시 전체 완료 진료 기준 · 분할결제와 환불은 중복 가능 · 오류·성과 순위 아님')

report=f'''목적: 분석 가능한 주제·Silver·Gold·발표 제안. 입력: 수정 합성 CSV 및 최종 DB 로컬 캐시. 출력: 실행 결과와 발표용 차트.

추천 발표 제목
「정상 대사 이후의 수납 업무 개선: 분할결제·환불 합산 확인과 업무 복잡도 시나리오」

결론
데이터에 차이가 없는 부분에서 문제를 만들어내지 않는다. 최종 기록의 정상 대사 결과를 먼저 제시하고, 분할결제·환불의 합산 확인 규모와 수정 합성자료의 업무 복잡도 민감도로 개선 방향을 제안한다. 균등한 분포는 세부 집단 우열 분석의 한계이지 모든 분석이 불가능하다는 뜻은 아니다.

자료와 계산 위치
1. 최종 MySQL 조회 캐시: 서버 표시 2026-10-15 19:23:48, 진료 {len(f):,}건, 거래 {len(p):,}건. 이번에는 DB 접속하지 않음.
2. 수정 합성자료: {manifest['dataset_id']}, 생성 {manifest['created_kst']}. fyi 폴더 CSV 4개 SHA256 일치 확인. 이전 생성본·draft·재현복제본은 합산하지 않음.
3. SQLite 메모리에서 S01~S08 SELECT 실행. SQL은 MySQL 8 호환 문법으로 작성했지만 현재 MySQL 실행 미검증. final_*는 로컬 캐시 논리명이다. DB에 테이블을 생성하거나 적재할 필요가 있다는 뜻이 아니다.
4. 수정본의 시나리오는 생성 가정이며 최종 캐시에 scenario_id는 없다. 표본을 전체 병원으로 일반화하지 않는다.

가능한 주제 순위
A(주제 중심): 분할결제·환불 합산 확인 규모 → S01/S08 → 통합 대사 화면과 원결제 추적 제안. 병원 차이가 작아도 건수 기준 처리 규모를 설명 가능.
A(가정 실험): 수납 업무 복잡화에 따른 작업량 민감도 → S02 → 재확인 단계의 조건부 수행·중복 확인 방지 제안. 인과 효과가 아니라 가정 계산.
B(자료 관리): 대사 근거 차이·불완전 근거를 분리하는 점검 체계 → S03/S04 → 기준 버전 표시와 보류 사유 분리. 과거 입력 판정을 현재 오류로 주장하면 안 됨.
B(확장): 추가 예약 요청 증가와 제안가능 구조 → S05/S06 → 활성·비활성 분모와 제안가능/확정 구분. 현 자료에서 대기 병목을 주장할 수 없음.
C(민감도만): 서비스 시간 대용값 변화 → S07 → 코드별 가정 비교. WORKLOAD_UP 25% 증가는 설계값이며 새로운 발견 아님.
제외: 의사 가용시간 감소의 효과(가용시간 0행), 실제 미수금·손실, 업무시간 절감 실적, 지원금 효과, 감염병 영향, 인력 부족 인과 분석.

G01 질문: 재정 대사에서 실제 확인 필요한 차이가 있는가?
숫자·분모: 완료 진료 496,863건 중 비교 가능 496,863건, 일치 496,863건(100%), 차이·보류·결제 부재 0건. 결제합 19,568,700,200원, 환불합 187,079,340원, 순기록 19,381,620,860원.
해석: 보존된 최종 캐시에서는 금액 차이를 발견하지 못했다.
개선 방향: 오류가 발생했다는 주장이 아니라 이 검증을 상시 실행하는 모니터링 절차를 제안한다.
한계: 정제 후 남은 기록의 결과이며 실제 납부 상태나 제외된 진료의 재무 상태를 보장하지 않는다.

G02 질문: 정상 대사 상태에서도 합산 확인 기능이 필요한 규모는?
숫자·분모: 전체 496,863건 중 분할결제 188,105건(37.86%), 환불 47,496건(9.56%). 두 집단 중복 가능, 합산하여 고유 대상을 만들지 않는다.
해석: 오류가 아니라 복수 거래를 진료 단위로 묶어 확인해야 하는 기록 규모다.
개선 방향: 진료별 서비스 합계·결제합·환불합을 먼저 집계한 화면, 원결제 연결·누적 환불 한도와 승인액 대사, 확인 이력 제공.
한계: 다회 거래가 업무 지연이나 비효율을 발생시켰다는 실측 자료는 없다.

G03 질문: 업무 복잡화 가정에서 작업분은 얼마나 달라지는가?
숫자·분모: 동일 결제 1,749건. BASE 3,498작업·20,937분 → COLLECTION_COMPLEX 5,247작업·46,920분. 증가 25,983분(+124.10%), 약 2.241배.
해석: 작업 2개→3개 및 개별 작업시간 1.5배라는 생성 규칙의 결합 결과다. 실제 운영에서 관찰한 증가는 아니다.
개선 방향: 재확인 조건을 명확히 하고 중복 확인을 줄이는 설계안을 실험한다. 예: 복잡화 가정 RECHECK 15,514.5 작업분 중 50%가 불필요한 반복이라고 추가 가정하면 7,757.25 작업분 감소, 남는 총량 39,162.75 작업분. 실제 절감효과가 아닌 균등 감소 민감도다.
한계: 담당자 식별·대기시간·동시작업 정보가 없어 FTE·근무시간·비용 절감으로 환산하지 않는다. 재확인 축소의 품질 영향은 별도 검증 필요.

G04 질문: 대사 근거의 불완전성과 금액 차이를 구분할 수 있는가?
숫자·분모: 수정본 BASE RECONCILE 1,749건 중 일치 1,686건(96.40%), 차이 19건(1.09%), 입력 기준 차이 보류 37건(2.12%), 불완전 근거 보류 7건(0.40%). 반올림 합계 주의.
해석: 19건의 차이와 44건의 근거 보류는 별개의 확인 경로다. 이 판정은 수정본 생성 당시 로컬 기준이다.
개선 방향: 기준 버전·자료 기준시점·보류 사유를 표시하고, 근거 확보 후 재대사한다.
한계: 최종 캐시와 연결 {linked:,}/1,749건({linked/1749:.2%}), 미연결 {1749-linked:,}건. 연결된 키라도 과거 판정을 현재 오류로 전용하지 않는다.
추가 연결 검증: 과거 금액 차이 19건은 모두 최종 캐시 미연결이다. 과거 입력 기준 차이 보류 37건 중 10건만 연결된다. 최종 기록의 정상 대사 결과와 과거 판정을 합쳐 오류 건수를 만들지 않는다.

G05 질문: 수요 증가 가정에서 대기 병목이 나타났는가?
숫자·분모: BASE 활성 1,944건 중 제안가능 1,669건(85.85%); DEMAND_UP 활성 3,888건 중 3,366건(86.57%). WAITLIST는 두 가정 모두 0건. 철회는 각각 275/522건.
해석: 요청을 두 배로 설정했으나 이 표본에서는 대기 발생을 발견하지 못했다. 비율 변화는 약 +0.72%p이며 같은 사람의 행동 변화가 아니다.
개선 방향: 실제 병목을 평가하려면 포화 세션·대기·취소 후 재배정 자료를 확보한다.
한계: 원자료의 예약 건수에는 취소·재전송이 포함될 수 있어 가용 수량 추정은 보수적인 합성 규칙이다. 현 결과로 인력 확충 필요성을 주장하지 않는다.

TO-BE
진료별 대사 → 실제 납부 상태 확인 → 상담 의향 확인 → 동의 → 최소 정보 확인 → 담당자 검토 → 적합한 의료비 지원 제도 안내 → 결정·입금·잔액 추적.
기록 차이로 경제적 어려움을 추정하지 않음. 환자 의료비 지원과 병원 운영 지원은 별도. 개인정보 수집·자격 판정·신청 기능 없음.
감염병 유행 전·중·후 비교는 향후 비교 가능한 자료 확보 후 확장할 방향임.

미검증 사항
현재 MySQL 재실행, 수정본의 현재 DB 전체 부모키 검증, 실제 직원 업무시간 및 개선 효과, 업무량 가정의 외적 타당성. 외부 의료환경 통계는 이번 오프라인 추가 분석에서 새로 수집하거나 갱신하지 않음.
'''
(ROOT/'주제별_Gold_분석리포트.txt').write_text(report,encoding='utf-8-sig')
(ROOT/'발표구성.txt').write_text('''목적: 발표 구성. 입력: 검증된 로컬 분석. 출력: 7장 발표 메시지와 차트 배치.
1. 문제 정의: 정상 대사 이후에도 복수 거래의 합산 확인이 필요하다. 전체 진료 496,863건, 차이 0건을 함께 제시.
2. 자료의 역할: 최종 캐시=기록 대사, 수정 합성자료=업무 가정 실험. 표본·기준시점을 분리. charts/03_linkage.png.
3. 확인 규모: 분할결제 37.86%, 환불 9.56%. charts/05_finance_volume.png. 오류 순위로 말하지 않음.
4. 핵심 실험: 동일 1,749건의 기본·복잡화 가정 비교. charts/01_workload.png. +124.10%는 생성 규칙 결과.
5. 점검 경로: 금액 차이와 근거 보류를 구분. charts/02_evidence.png. 과거 로컬 판정이라는 부제 필수.
6. 개선 제안: 진료별 합산 대사→근거 확인→조건부 재확인→이력 관리. 실제 절감효과는 후속 파일럿에서 측정.
7. 한계와 확장: 대기 0건(차트04는 부록), 가용시간 0행. 지원 연계 및 감염병 전중후 분석은 향후 과제.
발표 문장: “차이가 없다는 결과를 숨기지 않고, 정상 대사를 유지하면서 확인 절차의 복잡도를 관리하는 방향을 제안합니다.”
''',encoding='utf-8-sig')
metadata={'author':'Team 3','purpose':'오프라인 수정 합성자료 분석 검증','engine':sqlite3.sqlite_version,'mysql_connected':False,'source_dataset':manifest['dataset_id'],'checks':checks,'sql_result_rows':{k:len(v) for k,v in queries.items()},'linked_payments':linked,'unlinked_payments':1749-linked}
(ROOT/'검증결과.json').write_text(json.dumps(metadata,ensure_ascii=False,indent=2),encoding='utf-8')
(ROOT/'requirements.txt').write_text('# 목적: 오프라인 분석 실행 의존성; 입력: Python 환경; 출력: 분석/차트\npandas>=3.0\npyarrow>=26\nplotly>=7\nplaywright>=1.64\n',encoding='utf-8')
(ROOT/'실행안내.txt').write_text('목적: 분석 재실행. 입력: 기존 로컬 CSV/Parquet. 출력: 결과·차트. DB 불필요.\n프로젝트 루트에서:\n.\\.venv\\Scripts\\python.exe baek\\offline_topic_analysis_20261015\\build_analysis.py\n.\\.venv\\Scripts\\python.exe baek\\offline_topic_analysis_20261015\\render_charts.py\nSQL의 final_*는 실제 MySQL 테이블이 아닌 로컬 캐시 별칭. SQL 결과 CSV는 표준 헤더를 보존하며 작성자·목적은 이 안내와 SQL 주석에 기록.\n',encoding='utf-8-sig')
print(json.dumps(metadata,ensure_ascii=False,indent=2))
