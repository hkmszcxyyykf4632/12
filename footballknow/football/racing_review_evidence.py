"""Evidence from the exact official race, without historical or causal substitution."""
from copy import deepcopy
from datetime import datetime
from math import isfinite

from .evidence_reviews import add_fact, add_source, new_dossier
from .hkjc_public import ENDPOINT
from .racing import FOLDER, HORSE_ID, RACE_ID, load, placing


def course_code(value):
    return {'沙田': 'ST', '跑馬地': 'HV', '跑马地': 'HV'}.get(value, value)


def positive(value):
    try:
        number = float(value)
        return number if isfinite(number) and number > 0 else None
    except (TypeError, ValueError):
        return None


def timestamp(value):
    try:
        parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
        return parsed if parsed.tzinfo else None
    except (TypeError, ValueError, AttributeError):
        return None


def same_race(value, race):
    return (value.get('raceId') == race['id'] and value.get('date') == race['date']
            and course_code(value.get('course')) == race['course']
            and positive(value.get('distance')) == positive(race.get('distance'))
            and positive(race.get('distance')) is not None)


def same_placing(value, entry):
    place = placing(str(value.get('position', '')))
    if value.get('place') is not None and value.get('place') != entry.get('place'):
        return False
    if entry.get('place') is not None:
        return place == entry['place'] or not value.get('position') and value.get('place') == entry['place']
    return bool(value.get('position')) and value.get('position') == entry.get('position')


def build_dossier(race, original):
    """Read local evidence only; the caller supplies get_race's official result."""
    match = RACE_ID.fullmatch(race.get('id', ''))
    if (not match or race.get('date') != match[1] or race.get('course') != match[2]
            or race.get('status') != 'finished' or race.get('resultOfficial') is not True
            or not any(e.get('place') == 1 for e in race.get('entries', []))):
        raise ValueError('正式赛果或赛事身份尚未核实。')
    entries = race['entries']
    ids = [e.get('id', '') for e in entries]
    if len(set(ids)) != len(ids) or not all(HORSE_ID.fullmatch(ident) for ident in ids):
        raise ValueError('正式赛果马匹身份不一致。')
    d = new_dossier('racing', race['id'], deepcopy(original))
    result_source = add_source(d, race.get('source'), '马会本场正式赛果', race.get('updatedAt'))
    event_time = race.get('offTime') or race['date']
    header = f"{race['date']} {race.get('courseName') or race['course']} 第{match[3]}场；途程 {race.get('distance') or '未记录'}米"
    for key, label in [('class', '班次'), ('track', '跑道'), ('going', '场地状况')]:
        if race.get(key):
            header += f"；{label} {race[key]}"
    add_fact(d, header, [result_source], category='result', time=event_time, before_event=False)
    winners = [e['name'] for e in entries if e.get('place') == 1]
    d['overview'].append('本场冠军：' + '、'.join(winners) + '。')
    if original:
        picked = next((e for e in entries if e['id'] == original.get('pick')), None)
        if picked:
            d['overview'].append(f"原赛前首选 {picked['name']}，本场名次 {picked.get('position') or picked.get('place') or '未记录'}。")
        else:
            d['gaps'].append('原赛前首选身份未能与本场正式名单核对，不评价命中。')
    else:
        d['gaps'].append('本站未保存本场赛前预测，不能补造原选择或评价原预测方法。')

    d['raceContext'] = {'entries': [], 'distance': race.get('distance')}
    by_id = {e['id']: e for e in entries}
    for entry in entries:
        name = f"{entry.get('number', '')}号 {entry['name']}（{entry['id'].rsplit('_', 1)[-1]}）"
        parts = [f"{name}：{'退出' if entry.get('withdrawn') else '名次 ' + str(entry.get('position') or entry.get('place') or '未记录')}"]
        for key, label in [('running', '沿途走位'), ('finishTime', '完成时间'), ('margin', '头马距离'),
                           ('draw', '档位'), ('weight', '负磅'), ('bodyWeight', '体重')]:
            if entry.get(key) not in (None, ''):
                parts.append(f'{label} {entry[key]}')
        for key, label in [('jockey', '骑师'), ('trainer', '练马师')]:
            person = entry.get(key) or {}
            if person.get('name'):
                parts.append(f"{label} {person['name']}")
        fact = add_fact(d, '；'.join(parts) + '。', [result_source], category='result', time=event_time, before_event=False)
        d['timeline'].append({'time': event_time, 'text': '；'.join(parts) + '。', 'evidenceIds': [fact]})
        d['raceContext']['entries'].append({**{k: entry.get(k) for k in ('id', 'name', 'number', 'place', 'withdrawn')}, 'evidenceIds': [fact]})
        if entry.get('running'):
            add_fact(d, f"{name}：沿途走位 {entry['running']}；最终名次 {entry.get('position') or entry.get('place') or '未记录'}。",
                     [result_source], category='running', time=event_time, before_event=False)
        if positive(entry.get('winOdds')):
            add_fact(d, f"{name}：正式赛果所列独赢赔率 {entry['winOdds']}；这是赛后结果记录。",
                     [result_source], category='odds', time=event_time, before_event=False)
        cached = load(FOLDER / 'horses' / (entry['id'] + '.json'))
        records = [r for r in cached.get('records', []) if same_race(r, race)
                   and same_placing(r, entry) and r.get('horseId', entry['id']) == entry['id']]
        if cached.get('id') != entry['id']:
            records = []
        if len(records) == 1:
            record = records[0]
            supplements = [f'{label} {record[key]}' for key, label in
                           [('running', '沿途走位'), ('finishTime', '完成时间')]
                           if not entry.get(key) and record.get(key)]
            if supplements:
                record_source = add_source(d, record.get('source') or cached.get('source'),
                                           f"{entry['name']}本场往绩记录", cached.get('updatedAt'))
                fact = add_fact(d, name + '：本场往绩记录；' + '；'.join(supplements) + '。',
                                [record_source], category='result', time=event_time, before_event=False)
                d['timeline'].append({'time': event_time, 'text': name + '；' + '；'.join(supplements), 'evidenceIds': [fact]})
        equipment = entry.get('equipment')
        source = result_source
        if not equipment and len(records) == 1:
            equipment = records[0].get('equipment')
            source = add_source(d, records[0].get('source') or cached.get('source'),
                                f"{entry['name']}本场往绩记录", cached.get('updatedAt'))
        if equipment:
            add_fact(d, f'{name}：本场装备 {equipment}；没有与已保存赛前装备记录比较时，不视为临场更换。',
                     [source], category='equipment', time=event_time, before_event=False)

    raw = load(FOLDER / 'sectionals' / (race['id'] + '.json'))
    rows = raw.get('horses', [])
    valid = same_race(raw, race) and bool(rows)
    seen = set()
    for row in rows:
        entry = by_id.get(row.get('horseId'))
        if (not entry or row.get('horseId') in seen or not same_placing(row, entry)
                or row.get('finishTime') and entry.get('finishTime') and row['finishTime'] != entry['finishTime']):
            valid = False
        seen.add(row.get('horseId'))
    available = 0
    if valid:
        section_source = add_source(d, raw.get('source'), '马会本场分段时间', raw.get('fetchedAt'))
        for row in rows:
            splits = row.get('splits', [])
            if (not splits or any(not positive(s.get('metres')) or not positive(s.get('seconds')) for s in splits)
                    or sum(s['metres'] for s in splits) != race['distance']):
                continue
            name = by_id[row['horseId']]['name']
            values = []
            for index, split in enumerate(splits, 1):
                value = f"第{index}段 {split['metres']}米 {split['seconds']}秒"
                if split.get('position') is not None:
                    value += f"（走位 {split['position']}）"
                values.append(value)
            add_fact(d, f"{name}：本场 {race['distance']}米实录；" + '；'.join(values) + '。',
                     [section_source], category='sectionals', time=event_time, before_event=False)
            available += 1
    runners = sum(not e.get('withdrawn') for e in entries)
    d['overview'].append(f'经身份、名次及距离核对的本场分段覆盖 {available}/{runners} 匹实际出赛马。')
    if available < runners:
        d['gaps'].append('本场分段未齐或身份、名次、途程核对不通过；未使用历史分段替代本场记录。')
    d['gaps'].append('未收录可核对的本场竞赛董事报告，不能认定受阻、骑师决策、伤患或装备导致赛果。')
    d['gaps'].append('赔率不是资金量；未保存完整赔率时间序列，不能认定开盘、封盘、资金流向或走势造成赛果。')
    off = timestamp(race.get('offTime'))
    early_samples = 0
    for pool in race.get('pools', []):
        if pool.get('type') != 'WIN':
            continue
        by_number = {str(e.get('number')): e for e in entries}
        for quote in pool.get('quotes', []):
            entry = by_number.get(str(quote.get('combination')))
            first_at, first = timestamp(quote.get('firstAt')), positive(quote.get('first'))
            if not entry or not off or not first_at or not first or first_at >= off:
                continue
            source = add_source(d, ENDPOINT, f"马会公开数据接口：{entry['name']}首次独赢赔率采样", quote['firstAt'])
            fact = add_fact(d, f"{entry['name']}：本站赛前首次记录独赢赔率 {first:g}，采样于 {quote['firstAt']}。",
                            [source], category='odds', time=quote['firstAt'], before_event=True)
            d['timeline'].append({'time': quote['firstAt'], 'text': f"{entry['name']}首次赔率采样 {first:g}", 'evidenceIds': [fact]})
            early_samples += 1
            latest_at, latest = timestamp(pool.get('sourceUpdatedAt')), positive(quote.get('value'))
            if latest_at and latest and first_at < latest_at < off and not pool.get('quoteRetained'):
                direction = '下降' if latest < first else '上升' if latest > first else '不变'
                later_source = add_source(d, ENDPOINT, f"马会公开数据接口：{entry['name']}较晚独赢赔率采样", pool['sourceUpdatedAt'])
                fact = add_fact(d, f"{entry['name']}：较晚赛前记录独赢赔率 {latest:g}，相较首次记录 {first:g} {direction}；仅比较两个采样时点。",
                                [source, later_source], category='odds', time=pool['sourceUpdatedAt'], before_event=True)
                d['timeline'].append({'time': pool['sourceUpdatedAt'], 'text': f"{entry['name']}较晚赔率采样 {latest:g}", 'evidenceIds': [fact]})
    if not early_samples:
        d['gaps'].append('没有带可靠赛前时间戳的独赢赔率采样；赛果单一赔率不能说明赛前变化。')
    d['timeline'].sort(key=lambda item: timestamp(item['time']).timestamp() if timestamp(item['time']) else float('inf'))
    return d
