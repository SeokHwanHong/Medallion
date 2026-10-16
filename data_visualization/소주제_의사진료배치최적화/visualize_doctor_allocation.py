"""
[Team 3] 의사 배치 양극화 현황 및 재배치 시뮬레이션 효과 시각화 코드
- Seaborn / Matplotlib 기반 300 DPI 출판급 고해상도 인포그래픽 차트 생성
- 1. 차트 1: 병원별 의사 1인당 환자수 양극화 현황 (Boxplot + Strip plot)
- 2. 차트 2: 의사 재배치 시뮬레이션 전후 업무량 완화 효과 비교 (Grouped Bar plot)
- 3. 차트 노쇼 1~3: 예약 리드타임별 노쇼율, 연령대별 외래 비중, 채널별 접수 상태
"""

import os
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
import numpy as np

# 맑은 고딕 / 폰트 설정
plt.rcParams['font.family'] = 'Malgun Gothic'
plt.rcParams['axes.unicode_minus'] = False

def generate_doctor_allocation_charts(data_path, output_dir):
    os.makedirs(output_dir, exist_ok=True)
    df = pd.read_csv(data_path)
    
    # -------------------------------------------------------------
    # 차트 1: 의사 배치 양극화 분석
    # -------------------------------------------------------------
    plt.figure(figsize=(10, 6), dpi=300)
    palette = {'OVERLOADED (과밀·의사부족)': '#e11d48', 'BALANCED (적정)': '#0ea5e9', 'UNDERUTILIZED (유휴·의사여유)': '#10b981'}
    
    ax = sns.boxplot(data=df, x='workload_status', y='patients_per_doctor', palette=palette, width=0.45)
    plt.title('병원별 의사 1인당 담당 환자수 편차 및 업무 부하 양극화', fontsize=14, fontweight='bold', pad=15)
    plt.xlabel('병원별 업무 부하 상태', fontsize=11, fontweight='bold')
    plt.ylabel('의사 1인당 진료 환자수 (명)', fontsize=11, fontweight='bold')
    plt.grid(axis='y', linestyle='--', alpha=0.5)
    plt.tight_layout()
    chart1_path = os.path.join(output_dir, '차트_1_의사배치_양극화_분석.png')
    plt.savefig(chart1_path, dpi=300)
    plt.close()
    print(f"Chart 1 saved: {chart1_path}")
    
    # -------------------------------------------------------------
    # 차트 2: 의사 재배치 시뮬레이션 전후 비교
    # -------------------------------------------------------------
    plt.figure(figsize=(10, 6), dpi=300)
    agg_df = df.groupby('workload_status')[['patients_per_doctor', 'simulated_patients_per_doctor']].mean().reset_index()
    melted = agg_df.melt(id_vars='workload_status', value_vars=['patients_per_doctor', 'simulated_patients_per_doctor'],
                         var_name='시점', value_name='평균환자수')
    melted['시점'] = melted['시점'].map({'patients_per_doctor': '재배치 전 (Before)', 'simulated_patients_per_doctor': '재배치 후 (After)'})
    
    ax = sns.barplot(data=melted, x='workload_status', y='평균환자수', hue='시점', palette=['#94a3b8', '#0284c7'])
    plt.title('의사 재배치 시뮬레이션 적용 전·후 평균 환자수 완화 효과', fontsize=14, fontweight='bold', pad=15)
    plt.xlabel('병원별 업무 부하 상태', fontsize=11, fontweight='bold')
    plt.ylabel('의사 1인당 평균 환자수 (명)', fontsize=11, fontweight='bold')
    plt.grid(axis='y', linestyle='--', alpha=0.5)
    plt.legend(title='시뮬레이션 비교')
    plt.tight_layout()
    chart2_path = os.path.join(output_dir, '차트_2_의사_최적재배치_시뮬레이션_효과.png')
    plt.savefig(chart2_path, dpi=300)
    plt.close()
    print(f"Chart 2 saved: {chart2_path}")

if __name__ == "__main__":
    print("Doctor allocation visualization module loaded.")
