import argparse
from pathlib import Path
import json
import charts
from charts import *

PROJECT=Path(__file__).resolve().parents[2]
TITLE='진료과·시간대별 현장접수 불가 패턴 분석을 통한 사전 방문 안내 개선'
parser=argparse.ArgumentParser(description='현재 CSV 스냅샷 전용 주장별 근거 보고서 생성')
parser.add_argument('--analysis-json',type=Path,default=PROJECT/'data_analysis'/TITLE/'analysis_results.json')
parser.add_argument('--output-dir',type=Path,default=PROJECT/'report')
args=parser.parse_args()
R=json.loads(args.analysis_json.read_text(encoding='utf-8'))
EXPECTED_HASHES={'01_walk_in_monthly_overview.csv': '7f19a9de1b4a101a2b8af23e78eba5a3b6134cb49ae407c4a6cf0a57cfbd644f', '02_department_rejection.csv': '81aa503c358c62d890b72a7341433b3a9471623755b8af8fcfe9c91f336acb7b', '03_department_time_rejection.csv': '850a5803539f1eb339c6dad432121e0e53b7bc13b90a3f16465d144463a72cde'}
if R.get('input_hashes')!=EXPECTED_HASHES:
 raise ValueError('보고서는 현재 CSV 스냅샷 전용입니다. 변경된 데이터에 맞춰 본문을 재검토하세요.')
charts.R=R
OUTPUT_DIR=args.output_dir;OUTPUT_DIR.mkdir(parents=True,exist_ok=True)
BASE=TITLE+'_주장별근거보고서';name=BASE+'.pdf';i=2
while (OUTPUT_DIR/name).exists():name=f'{BASE}_v{i}.pdf';i+=1
DEST=OUTPUT_DIR/name
O=R['total'];overall=100*O['rejected_count']/O['walk_in_count'];C=R['candidate'];top4=C[:4]
add('주장별 근거 보고서 | 분석 기간 2023.01~2025.12 | 작성 2026.10.16','small')
add(TITLE,'h1')
add('1. 진료과 전체의 비율 차이는 작지만, 시간대별 차이는 크다','h2')
add('<b>핵심 질문</b> 어느 진료과·도착 시간대의 현장접수 정책과 사전 안내를 먼저 점검할 것인가?')
table(['현장접수 기록','접수불가 기록','전체 접수불가율'],[['298,257건','73,471건','24.63%']],[169,169,169])
S.append(rate_chart())
add('도표 1. Y축: 진료과 / X축: 접수불가율(0~30%). 분모는 각 진료과 전체 WALK_IN이다. 우측은 REJECTED / WALK_IN 건수. 출처: CSV 02, 전체 기간 건수 합산. 전체 기준선은 CSV 01.','small')
add('<b>근거:</b> 진료과별 비율은 산부인과 23.65%~신경과 25.18%로 최대 차이는 <b>1.53%p</b>다. 전체 진료과를 단순히 고율·저율로 나누기보다 내부 시간대를 살펴볼 필요가 있다.')
add('<b>해석 범위:</b> 차이가 전혀 없거나 통계적으로 동일하다는 뜻은 아니다. 병원 수·운영일·인력으로 보정한 비교도 아니므로 업무 부담이나 의사 부족 순위로 해석하지 않는다.','small')
add('분석 기준','h2')
add('WALK_IN 접수 기록 1건을 단위로 하며 고유 환자·확정 방문 수가 아니다. 월·시간은 실제 도착 시각 기준이다. 접수불가율은 REJECTED ÷ 해당 집단 전체 WALK_IN × 100이며, 건수를 합산한 뒤 재계산했다. 서로 다른 CSV의 동일 모집단은 더하지 않았다.','small')

page('2. 같은 진료과 안에서도 시간대별 차이가 나타난다')
add('<b>주장 ②</b> 시간대별 비율 차이는 진료과 전체 평균에 가려져 있으며, 월별 반복성 확인이 필요하다.')
S.append(heat_chart())
add('도표 2. Y축: 진료과 / X축: 도착 1시간 구간. 값과 색은 REJECTED ÷ 해당 진료과·시간대 WALK_IN(%), 공통 범위 0~60%. NA는 미관측이며 관측 0%와 구분한다. 출처: CSV 03, 요일·월을 합친 전체 기간 집계.','small')
table(['같은 진료과 내 비교 예시','접수불가율','진료과 전체'],[
 ('신경과 12시대 / 9·11시대','49.98% / 0%','25.18%'),
 ('가정의학과 9시대 / 11·14시대','49.94% / 0%','24.64%'),
],[235,150,122])
add('<b>근거:</b> 12개 진료과×8~14시의 표시 셀 중 39개 조합에 접수 기록이 있다. 관측된 구간은 0%와 약 50%로 크게 나뉘어, 진료과 전체 비율만으로는 드러나지 않는 내부 차이를 보여준다.')
add('<b>다음 확인:</b> 전체 기간의 높은 비율만으로 선정하지 않고, 같은 월·진료과 평균보다 높은 상태가 여러 달 반복되는지 확인한다. 기록이 없는 달·시간대를 0으로 채우지 않는다.')
add('<b>주의:</b> 합성 자료의 0%·약 50% 반복은 생성 규칙의 영향일 수 있다. 높은 비율은 실제 운영 원인을 밝힌 결과가 아니며, 0%는 진료를 보장하는 시간이라는 뜻이 아니다.','small')

page('3. 반복성을 확인하고 발생 건수로 점검 순서를 정한다')
add('<b>반복 기준:</b> 같은 월·진료과 전체보다 ≥5%p 높은 달이 관측 월의 ≥2/3인 구간을 찾았다. 기준에는 해당 시간대 자신도 포함된다. 5%p·2/3는 분석상 기준이며 업무 표준·유의성 기준이 아니다.','small')
S.append(trend_chart())
add('도표 3. X축: 월 / Y축: 접수불가율(%), 모든 패널 0~60%. 주황 분모: 해당 월·진료과·시간대 WALK_IN, 파랑 분모: 같은 월·진료과 전체 WALK_IN. 출처: CSV 03·02.','small')
add('<b>주장 ③</b> 반복 고율 구간 중 접수불가 건수가 많은 곳부터 점검할 수 있다. 점검 범위를 좁히기 위해 반복 고율 후보 중 접수불가 건수 상위 4개를 선정했다.')
table(['진료과·시간대','현장(건)','불가(건)','불가율','기준 충족/관측(개월)','최소 월 건수'],[(f"{r['department_name']} {r['arrival_hour']}시대",n(r['walk_in_count']),n(r['rejected_count']),pct(r['rate']),'36/36',n(r['min_monthly_n'])) for r in top4],[131,78,78,68,77,75])
add('네 구간 모두 36개월 기준을 충족했다. 접수불가는 합계 <b>24,996건, 전체 불가 기록의 34.02%</b>다. 이는 과거 기록의 포함 비중이며 예방 가능 비율·효과 순위가 아니다.')
add('비율 차이 0·5·10%p와 반복 1/2·2/3·3/4의 9개 조합 모두 후보 집합이 유지됐지만, 통계적 유의성이나 실제 적용 타당성을 뜻하지는 않는다.','small')
add('월별 접수 분모를 확인했으며, 네 구간의 최소 월 건수는 264~293건이다. 특정 월의 소수 기록만으로 만들어진 결과는 아니다. 다만 반복성도 생성 구조에서 비롯될 수 있다. 12시대는 12:00~12:59 도착 기록이며 접수 마감 시각과 같지 않다.','small')

page('4. 근거를 사전 안내 점검 행동으로 연결한다')
table(['확인한 근거','결론·활용 범위'],[
 ('진료과 전체 차이 1.53%p','진료과 단독 순위보다 시간대까지 함께 비교한다.'),
 ('시간대별 차이·36개월 반복','자료 내 지속적 패턴이 확인된 구간을 점검 대상으로 삼는다.'),
 ('상위 네 구간: 불가 24,996건','발생 규모가 큰 곳부터 정책·안내 점검을 시작한다.'),
],[215,292])
add('개선 실행: 확인 → 대조 → 반영','h2')
table(['단계','실행 내용','확인할 결과'],[
 ('① 정책 확인','선정 구간의 실제 접수 정책·조건을 병원별로 확인한다.','접수 조건과 공식 문의 경로'),
 ('② 안내 대조','확인된 정책과 기존 방문 전 안내 내용을 대조한다.','안내 누락·불명확한 문구의 유무'),
 ('③ 조건부 반영','보완 필요가 확인되면, 실제 사용하는 방문 전 채널에 조건·문의 경로를 반영한다.','병원 확인을 거친 안내 문구'),
],[85,250,172])
add('병원 확인 후 사용할 안내 예시','h2')
add('<b>“방문 전 해당 진료과의 현장접수 가능 여부를 확인해 주세요.”</b>')
add('홈페이지·예약 안내 등 실제 사용하는 채널과 문의처는 확인이 필요하다. 병원별 정책을 확인하지 않고 일괄 적용하지 않는다. 현재 집계로 실시간 접수 가능 여부를 제공할 수는 없다.','small')
add('최종 결론','h2')
add('<b>진료과 평균에 가려진 시간대별 접수불가 차이를 확인했다. 반복성과 발생 규모를 근거로 실제 접수 정책과 사전 안내를 우선 점검할 네 구간을 선정했다.</b>')
add('확인하지 못한 것','h2')
add('합성 생성 규칙이 패턴과 반복성에 영향을 주었을 수 있다. 접수불가 사유·기존 안내 노출 정보가 없어 안내 부족을 원인으로 단정할 수 없다. 안내 개선의 실제 효과는 별도 검증이 필요하다.')
add('자료·검증','h2')
add('01_walk_in_monthly_overview.csv / 02_department_rejection.csv / 03_department_time_rejection.csv. 36개월 월별 합계 대사, 분자·분모 재계산, 후보 선정·반복 개월·상위 합계와 민감도 재검증을 수행했다. SEEN·LEFT·REJECTED·UNKNOWN을 구분했고 반복 진단값은 합산하지 않았다. DB 접속이나 기존 파일 변경 없이 작성했다.','small')
def footer(c,doc):
 c.setStrokeColor(LIGHT);c.line(44,39,551,39);label(c,44,24,'현장접수 불가 패턴 | 주장별 근거 보고서 | 2026.10.16',7,GRAY);label(c,551,24,doc.page,8,GRAY,'right')
doc=SimpleDocTemplate(str(DEST),pagesize=(595.28,841.89),leftMargin=44,rightMargin=44,topMargin=36,bottomMargin=50,title=TITLE+' - 주장별근거보고서')
doc.build(S,onFirstPage=footer,onLaterPages=footer)
print(f'Report saved: {DEST}')
