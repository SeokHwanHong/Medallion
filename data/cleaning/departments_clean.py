"""Standalone cleaner. Policy: hospital specification sheets 02/03/15, B01/B02/B13-B16.
Run with the project .venv Python; only this script directory is written.
_csv_line is a 1-based CSV record position including the header (not a byte offset).
"""
from pathlib import Path
from datetime import datetime
import shutil
import json
import re
import polars as pl
OUT = Path(__file__).resolve().parent
PROJECT = OUT.parent.parent
DATA = PROJECT / 'data_corrupted' / 'data'
CONFIG = {'departments': {'columns': ['department_code', 'department_name', 'source_system'], 'pk': 'department_code', 'ids': {'department_code': 'DEP'}, 'lengths': {'department_code': 32, 'department_name': 100, 'source_system': 8}}}

def read_table(name):
    files = sorted((DATA / name).glob('*.csv'))
    if not files:
        raise FileNotFoundError(f'CSV 파일이 없습니다: {DATA / name}')
    parts = []
    for file in files:
        df = pl.read_csv(file, infer_schema=False, row_index_name='_line')
        df = df.with_columns((pl.col('_line') + 2).alias('_csv_line'), pl.lit(file.name).alias('_file')).drop('_line')
        parts.append(df)
    return pl.concat(parts).with_row_index('_row_id')

def strip_strings(df, columns):
    return df.with_columns([pl.col(column).str.strip_chars().replace('', None).alias(column) for column in columns])

def save_csv(df, path):
    df.write_csv(path, include_bom=False, date_format='%Y-%m-%d', datetime_format='%Y-%m-%d %H:%M:%S', null_value='', line_terminator='\r\n')

def clean_table():
    name = 'departments'
    cfg = CONFIG[name]
    pk = cfg['pk']
    print(f'\n[{name}] 원본 읽는 중...', flush=True)
    raw = read_table(name)
    columns = [c for c in raw.columns if not c.startswith('_')]
    if columns != cfg['columns']:
        raise ValueError(f"{name}의 컬럼 구성이 명세와 다릅니다.\n예상: {cfg['columns']}\n실제: {columns}")
    print(f'[{name}] 원본 {raw.height:,}행', flush=True)
    df = strip_strings(raw, columns)
    df = df.with_columns([pl.col(column).str.replace_all('-', '_') for column in cfg['ids']])
    domains = []
    allowed_codes = {}
    for column in domains:
        df, allowed_codes[column] = code_map(df, column)
    normalized = df
    print(f'[{name}] 중복·자료형 검사 중...', flush=True)
    df = df.unique(subset=columns, keep='first', maintain_order=True)
    excluded_ids = normalized.join(df.select('_row_id'), on='_row_id', how='anti').select('_row_id')
    df = df.with_columns((pl.len().over(pk) > 1).alias('_pk_conflict'))
    rules = {'PK_CONFLICT': pl.col('_pk_conflict')}
    for column in columns:
        if column != 'original_payment_id':
            rules['NULL_OR_TYPE:' + column] = pl.col(column).is_null()
    for column, prefix in cfg['ids'].items():
        rules['ID_FORMAT:' + column] = pl.col(column).is_not_null() & ~pl.col(column).str.contains(f'^{prefix}_[0-9]{{9}}$')
    for column, size in cfg['lengths'].items():
        rules['LENGTH:' + column] = pl.col(column).str.len_chars() > size
    rules['SOURCE_SYSTEM'] = pl.col('source_system').is_not_null() & ~pl.col('source_system').is_in(['LEGACY_A', 'LEGACY_B'])
    for column, allowed in allowed_codes.items():
        rules['UNREGISTERED:' + column] = pl.col(column).is_not_null() & ~pl.col(column).is_in(allowed)

    def add_fk(column, observed, usable):
        rules['FK_MISSING:' + column] = pl.col(column).is_not_null() & ~pl.col(column).is_in(observed.implode())
        rules['FK_PARENT_UNUSABLE:' + column] = pl.col(column).is_in(observed.implode()) & ~pl.col(column).is_in(usable.implode())
    print(f'[{name}] 참조 관계 검사 중...', flush=True)
    df = df.with_columns([expr.fill_null(False).alias(key) for key, expr in rules.items()])
    df = df.with_columns(pl.concat_list([pl.when(pl.col(key)).then(pl.lit(key)).otherwise(pl.lit(None, dtype=pl.String)) for key in rules]).list.drop_nulls().alias('_issues'))
    accepted = df.filter(pl.col('_issues').list.len() == 0)
    bad = df.filter(pl.col('_issues').list.len() > 0)
    clean = accepted.select(columns)
    quarantine = raw.join(bad.select('_row_id', '_issues'), on='_row_id', how='inner').with_columns(pl.col('_issues').list.join(';'))
    excluded = raw.join(excluded_ids, on='_row_id', how='inner').with_columns(pl.lit('STANDARDIZED_EXACT_RETRANSMISSION').alias('_reason'))
    counts = pl.DataFrame({'rule': list(rules), 'affected_rows': [int(df[key].sum()) for key in rules]})
    assert raw.height == clean.height + quarantine.height + excluded.height, '원본과 결과의 행 수가 맞지 않습니다.'
    assert clean[pk].null_count() == 0, '정상 데이터에 PK 결측이 있습니다.'
    assert clean[pk].n_unique() == clean.height, '정상 데이터에 PK 중복이 있습니다.'
    assert DATA.resolve() != OUT.resolve() and DATA.resolve() not in OUT.resolve().parents, '출력 폴더는 원본 데이터 폴더 밖이어야 합니다.'
    print(f'[{name}] CSV 저장 중...', flush=True)
    destination = OUT
    destination.mkdir(parents=True, exist_ok=True)
    previous = list(destination.glob('*.csv')) + list(destination.glob('validation_*.json'))
    if previous:
        backup = PROJECT / 'backup' / (datetime.now().strftime('%Y%m%d_%H%M%S_%f') + '_' + 'departments')
        backup.mkdir(parents=True)
        for path in previous:
            shutil.copy2(path, backup / path.name)
    save_csv(clean, destination / f'silver_{name}.csv')
    save_csv(quarantine, destination / f'quarantine_{name}.csv')
    save_csv(excluded, destination / f'excluded_{name}.csv')
    provenance = accepted.select('_row_id', '_file', '_csv_line')
    save_csv(provenance, destination / f'provenance_{name}.csv')
    save_csv(counts, destination / f'rule_counts_{name}.csv')
    reread = pl.read_csv(destination / f'silver_{name}.csv', infer_schema=False)
    expected = clean.with_columns(pl.col('transacted_at').dt.strftime('%Y-%m-%d %H:%M:%S')) if 'transacted_at' in columns else clean
    expected = expected.with_columns(pl.all().cast(pl.String))
    assert reread.equals(expected), 'Saved silver values/schema/order differ'
    assert reread.columns == columns and reread.height == clean.height
    for path in destination.glob('*.csv'):
        content = path.read_bytes()
        assert not content.startswith(b'\xef\xbb\xbf'), path
        content.decode('utf-8')
        assert b'\n' not in content.replace(b'\r\n', b''), path
    pending = []
    if name == 'hospital_departments':
        pending = ['hospitals final silver validation: not performed; raw key format/conflict checks only']
    elif name == 'payments':
        pending = ['encounters final silver validation: not performed; raw key format/conflict checks only', 'B12 encounter total payment/refund/net_charge reconciliation: not performed (requires final encounters)']
    report = {'table': name, 'raw': raw.height, 'silver': clean.height, 'quarantine': quarantine.height, 'excluded': excluded.height, 'pk_nulls': clean[pk].null_count(), 'pk_unique': clean[pk].n_unique(), 'silver_roundtrip': True, 'utf8_no_bom_crlf': True, 'output': str(destination), 'pending': pending}
    (destination / f'validation_{name}.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(report, ensure_ascii=False), flush=True)
    print(f'\n[{name}] 완료')
    print({'원본': raw.height, '통과': clean.height, '격리': quarantine.height, '제외': excluded.height})
    print('저장 위치:', destination)
    return {'raw': raw, 'clean': clean, 'quarantine': quarantine, 'excluded': excluded, 'rules': counts}
if __name__ == '__main__':
    if not DATA.is_dir():
        raise SystemExit(f'원본 폴더가 없습니다: {DATA}')
    clean_table()
