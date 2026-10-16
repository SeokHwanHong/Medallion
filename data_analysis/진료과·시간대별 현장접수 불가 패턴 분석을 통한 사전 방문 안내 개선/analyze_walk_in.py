"""현장접수 CSV 01~03을 재집계한다. DB 연결과 입력 파일 변경은 하지 않는다."""
from pathlib import Path
import argparse
import hashlib
import json
import polars as pl


def analyze(input_dir):
    folder = Path(input_dir)
    names = ['01_walk_in_monthly_overview.csv', '02_department_rejection.csv',
             '03_department_time_rejection.csv']
    frames = [pl.read_csv(folder / name) for name in names]
    a, b, c = frames
    counts = ['walk_in_count', 'seen_count', 'left_count', 'rejected_count',
              'unknown_outcome_count']

    def aggregate(frame, keys):
        return frame.group_by(keys).agg([pl.col(k).sum() for k in counts]).with_columns(
            (100 * pl.col('rejected_count') / pl.col('walk_in_count')).alias('rate')
        ).sort(keys)

    month = aggregate(a, ['arrival_month'])
    if month['arrival_month'].to_list() != [f'{year}-{m:02}' for year in range(2023, 2026) for m in range(1, 13)]:
        raise ValueError('입력 기간은 2023-01~2025-12의 36개월이어야 합니다.')
    for frame in frames:
        if not aggregate(frame, ['arrival_month']).equals(month):
            raise ValueError('CSV 간 월별 합계가 일치하지 않습니다.')
        if frame.filter(pl.sum_horizontal([pl.col(k) for k in counts[1:]]) != pl.col('walk_in_count')).height:
            raise ValueError('접수 결과 합계와 전체 건수가 다릅니다.')
    total = {k: int(a[k].sum()) for k in counts}
    dept = aggregate(b, ['department_code', 'department_name']).with_columns(
        (100 * pl.col('rejected_count') / total['rejected_count']).alias('rejected_share'))
    dm = aggregate(b, ['arrival_month', 'department_code'])
    mh = aggregate(c, ['arrival_month', 'department_code', 'department_name', 'arrival_hour'])
    mh = mh.join(dm.select('arrival_month', 'department_code', pl.col('rate').alias('reference_rate')),
                 on=['arrival_month', 'department_code'], validate='m:1').with_columns(
        (pl.col('rate') - pl.col('reference_rate')).alias('delta_pp'))
    repeat = mh.group_by('department_code', 'department_name', 'arrival_hour').agg(
        pl.len().alias('observed_months'),
        pl.col('walk_in_count').sum(), pl.col('rejected_count').sum(),
        (pl.col('delta_pp') >= 5).sum().alias('qualified_months'),
        pl.col('walk_in_count').min().alias('min_monthly_n'),
        pl.col('rate').min().alias('min_monthly_rate'),
        pl.col('rate').max().alias('max_monthly_rate'),
        ((pl.col('delta_pp') * pl.col('walk_in_count')).sum() / pl.col('walk_in_count').sum()).alias('weighted_delta_pp')
    ).with_columns(
        (100 * pl.col('rejected_count') / pl.col('walk_in_count')).alias('rate'),
        (pl.col('qualified_months') / pl.col('observed_months')).alias('repeat_fraction'))
    candidate = repeat.filter(pl.col('repeat_fraction') >= 2 / 3).sort('rejected_count', descending=True)
    base = set(zip(candidate['department_code'], candidate['arrival_hour']))
    sensitivity = []
    for delta in [0, 5, 10]:
        for fraction in [1 / 2, 2 / 3, 3 / 4]:
            check = mh.group_by('department_code', 'arrival_hour').agg(
                pl.len().alias('n'), (pl.col('delta_pp') >= delta).sum().alias('k')
            ).filter(pl.col('k') / pl.col('n') >= fraction)
            pairs = set(zip(check['department_code'], check['arrival_hour']))
            sensitivity.append({'delta_pp': delta, 'repeat_threshold': fraction,
                                'candidate_count': len(pairs), 'same_as_base': pairs == base})
    return {'folder': str(folder.resolve()), 'total': total,
            'input_hashes': {name: hashlib.sha256((folder / name).read_bytes()).hexdigest() for name in names},
            'checks': {'monthly_totals_match': True, 'outcome_totals_match': True},
            'month': month.to_dicts(), 'dept': dept.to_dicts(),
            'heat': aggregate(c, ['department_code', 'department_name', 'arrival_hour']).to_dicts(),
            'mh': mh.to_dicts(), 'candidate': candidate.to_dicts(), 'sensitivity': sensitivity}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input-dir', type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument('--output', type=Path, default=Path(__file__).resolve().parent / 'analysis_results.json')
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(f'기존 결과를 덮어쓰지 않습니다. 다른 --output 경로를 지정하세요: {args.output}')
    result = analyze(args.input_dir)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('x', encoding='utf-8') as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2)
    print(f'분석 결과 저장: {args.output}')


if __name__ == '__main__':
    main()
