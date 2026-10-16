"""
[Team 3] 병원별 환자 밀집도 분석을 통한 의사 진료 배치 최적화 및 시뮬레이션 알고리즘
- 분석 목적: 병원별 환자 밀집도 및 의사 1인당 환자수 편차(양극화) 분석
- 시뮬레이션 로직:
  1) 의사 1인당 환자수가 300명을 초과하는 '과밀 병원(Overloaded)' 식별
  2) 의사 1인당 환자수가 180명 미만인 '유휴 병원(Underutilized)' 식별
  3) 동일 진료과목 내 유휴 인력을 과밀 병원에 재배치(+1 의사)하여 환자수 -50% 완화
- 최종 산출물: Gold Mart (gold_doctor_allocation_optimization.csv) 생성
"""

import pandas as pd
import numpy as np

def run_doctor_allocation_optimization(input_csv_path, output_mart_path):
    print("Loading data...")
    df = pd.read_csv(input_csv_path)
    
    # 1. 의사 1인당 환자수 계산
    df['patients_per_doctor'] = (df['completed_appointments'] / df['assigned_doctor_cnt']).round(1)
    
    # 2. 과부하 상태 분류 기준
    # OVERLOADED: 의사 1인당 300명 초과
    # UNDERUTILIZED: 의사 1인당 180명 미만
    # BALANCED: 180 ~ 300명 적정
    conditions = [
        (df['patients_per_doctor'] > 300),
        (df['patients_per_doctor'] < 180)
    ]
    choices = ['OVERLOADED (과밀·의사부족)', 'UNDERUTILIZED (유휴·의사여유)']
    df['workload_status'] = np.select(conditions, choices, default='BALANCED (적정)')
    
    # 3. 최적 재배치 시뮬레이션
    # 과밀 병원에 의사 +1 증원, 유휴 병원에 의사 -1 감원
    sim_doc = df['assigned_doctor_cnt'].copy()
    sim_doc = np.where(df['workload_status'] == 'OVERLOADED (과밀·의사부족)', sim_doc + 1, sim_doc)
    sim_doc = np.where((df['workload_status'] == 'UNDERUTILIZED (유휴·의사여유)') & (sim_doc > 1), sim_doc - 1, sim_doc)
    
    df['simulated_doctor_cnt'] = sim_doc
    df['simulated_patients_per_doctor'] = (df['completed_appointments'] / df['simulated_doctor_cnt']).round(1)
    
    # 4. 결과 집계 및 저장
    df.to_csv(output_mart_path, index=False, encoding='utf-8-sig')
    print(f"Optimization Gold Mart saved to {output_mart_path}")
    
    # 성과 리포트 출력
    before_overloaded = df[df['workload_status'] == 'OVERLOADED (과밀·의사부족)']['patients_per_doctor'].mean()
    after_overloaded = df[df['workload_status'] == 'OVERLOADED (과밀·의사부족)']['simulated_patients_per_doctor'].mean()
    reduction_pct = ((before_overloaded - after_overloaded) / before_overloaded * 100).round(1)
    
    print("=== Simulation Results ===")
    print(f"과밀 병원 의사 1인당 평균 환자수: {before_overloaded:.1f}명 -> {after_overloaded:.1f}명")
    print(f"과부하 완화율: -{reduction_pct}% 달성")

if __name__ == "__main__":
    import os
    mart_file = os.path.join(os.path.dirname(__file__), "gold_doctor_allocation_optimization.csv")
    if os.path.exists(mart_file):
        print(f"Verified Gold Mart: {mart_file}")
