"""분석 JSON으로 진료과 비교·히트맵·월별 반복성 도표를 생성한다."""
from pathlib import Path
import argparse
import json
import charts
from reportlab.platypus import SimpleDocTemplate
import pymupdf


def main():
    project = Path(__file__).resolve().parents[2]
    topic = Path(__file__).resolve().parent.name
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--analysis-json', type=Path,
                        default=project / 'data_analysis' / topic / 'analysis_results.json')
    parser.add_argument('--output-dir', type=Path, default=Path(__file__).resolve().parent)
    args = parser.parse_args()
    charts.R = json.loads(args.analysis_json.read_text(encoding='utf-8'))
    figures = [('01_department_comparison', charts.rate_chart),
               ('02_department_hour_heatmap', charts.heat_chart),
               ('03_monthly_repetition', charts.trend_chart)]
    if any((args.output_dir / (name + ext)).exists() for name, _ in figures for ext in ['.pdf', '.png']):
        raise FileExistsError('기존 도표를 덮어쓰지 않습니다. 다른 --output-dir을 지정하세요.')
    args.output_dir.mkdir(parents=True, exist_ok=True)
    for name, factory in figures:
        chart = factory()
        path = args.output_dir / (name + '.pdf')
        SimpleDocTemplate(str(path), pagesize=(charts.W + 24, chart.height + 24),
                          leftMargin=6, rightMargin=6, topMargin=6, bottomMargin=6).build([chart])
        with pymupdf.open(path) as pdf:
            assert len(pdf) == 1
            pdf[0].get_pixmap(matrix=pymupdf.Matrix(2, 2)).save(args.output_dir / (name + '.png'))
        print(f'도표 저장: {name}')


if __name__ == '__main__':
    main()
