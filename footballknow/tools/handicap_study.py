"""Reproducible, descriptive study of closing Asian handicaps, independent of forecasts."""
from __future__ import annotations

import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
import csv
from datetime import datetime, timezone
import hashlib
import io
import json
import math
from pathlib import Path
from urllib.request import Request, urlopen

LEAGUES = {'epl': ('英超', 'E0', 380), 'laliga': ('西甲', 'SP1', 380),
           'seriea': ('意甲', 'I1', 380), 'bundesliga': ('德甲', 'D1', 306)}
SEASONS = ['2025-26', '2024-25', '2023-24']
VERSION = 'closing-shallow-handicap-v1'
SOURCE = 'https://www.football-data.co.uk/'
OUTCOMES = {1.0: '全赢', .5: '赢半', 0.0: '走盘', -.5: '输半', -1.0: '全输'}


def number(value):
    try:
        n = float(value)
        return n if math.isfinite(n) else None
    except (ValueError, TypeError):
        return None


def handicap(value):
    n = number(value)
    return n if n is not None and abs(n) <= 10 and n * 4 == round(n * 4) else None


def price(value):
    n = number(value)
    return n if n is not None and 1 < n <= 1000 else None


def legs(line):
    return (line - .25, line + .25) if abs(round(line * 4)) % 2 else (line,)


def settlement(margin, line):
    values = [margin + x for x in legs(line)]
    return sum(1 if x > 0 else -1 if x < 0 else 0 for x in values) / len(values)


def profit(margin, line, decimal_price):
    return sum(decimal_price - 1 if margin + x > 0 else -1 if margin + x < 0 else 0
               for x in legs(line)) / len(legs(line))


def ratio(k, n):
    return round(k / n * 100, 2) if n else None


def proportion(k, n):
    if not n:
        return {'count': k, 'n': n, 'pct': None, 'interval95': None}
    p, z = k / n, 1.959963984540054
    centre = (p + z*z/(2*n))/(1+z*z/n)
    radius = z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/(1+z*z/n)
    return {'count': k, 'n': n, 'pct': ratio(k, n),
            'interval95': [round((centre-radius)*100, 2), round((centre+radius)*100, 2)]}


def parse(raw, season, league, source_url):
    parsed, audit, rejected, seen = [], Counter(), [], set()
    start_year = int(season[:4])
    reader = csv.DictReader(io.StringIO(raw.decode('utf-8-sig')))
    required = {'Div', 'Date', 'HomeTeam', 'AwayTeam', 'FTHG', 'FTAG', 'FTR', 'AHCh'}
    if not required.issubset(reader.fieldnames or []):
        raise ValueError(f'{source_url}: missing fields {required - set(reader.fieldnames or [])}')
    for row_number, row in enumerate(reader, 2):
        if not any(str(v or '').strip() for k, v in row.items() if k):
            continue
        audit['sourceRows'] += 1
        reason = None
        try:
            date = datetime.strptime(row['Date'], '%d/%m/%Y').date()
            assert datetime(start_year, 7, 1).date() <= date < datetime(start_year+1, 7, 1).date()
            hg, ag = number(row['FTHG']), number(row['FTAG'])
            assert hg is not None and ag is not None and hg.is_integer() and ag.is_integer()
            assert 0 <= hg <= 30 and 0 <= ag <= 30
            hg, ag = int(hg), int(ag)
            assert row['Div'] == LEAGUES[league][1]
            assert row['FTR'] == ('H' if hg > ag else 'A' if ag > hg else 'D')
            assert row['HomeTeam'] and row['AwayTeam'] and row['HomeTeam'] != row['AwayTeam']
            key = (date.isoformat(), row['HomeTeam'], row['AwayTeam'])
        except (AssertionError, ValueError, TypeError):
            reason = 'invalidResultOrIdentity'
        if not reason and key in seen:
            reason = 'duplicate'
        if reason:
            audit[reason] += 1
            rejected.append({'row': row_number, 'reason': reason})
            continue
        seen.add(key)
        audit['validResults'] += 1
        line = handicap(row['AHCh'])
        if line is None:
            audit['missingClosingLine' if not str(row['AHCh'] or '').strip() else 'invalidClosingLine'] += 1
            continue
        audit['validClosingLines'] += 1
        if abs(line) > .5:
            audit['outsideScope'] += 1
            audit['deepDraws'] += int(hg == ag)
            audit['deep00or11'] += int(hg == ag and hg <= 1)
            audit['deepCloseGame'] += int(abs(hg-ag) <= 1)
            audit['deepUnder25'] += int(hg+ag <= 2)
            continue
        audit['selected'] += 1
        early = handicap(row.get('AHh'))
        h_price, a_price = price(row.get('B365CAHH')), price(row.get('B365CAHA'))
        over, under = price(row.get('B365C>2.5')), price(row.get('B365C<2.5'))
        if line:
            fav = 'home' if line < 0 else 'away'
            fav_early = early if line < 0 else -early if early is not None else None
            if fav_early is None:
                movement = '无可比早盘'
            elif fav_early > 0:
                movement = '让受互换'
            elif -abs(line) < fav_early:
                movement = '让球加深'
            elif -abs(line) > fav_early:
                movement = '让球变浅'
            else:
                movement = '盘口不变'
        else:
            fav = None
            movement = '无可比早盘' if early is None else '退至平手' if early else '盘口不变'
        residual = hg-ag+line
        parsed.append({'id': f'{league}:{key[0]}:{key[1]}:{key[2]}', 'season': season,
            'league': league, 'date': date.isoformat(), 'home': row['HomeTeam'], 'away': row['AwayTeam'],
            'hg': hg, 'ag': ag, 'line': line, 'earlyLine': early, 'movement': movement,
            'residual': residual, 'distance': abs(residual), 'homeSettlement': settlement(hg-ag, line),
            'favorite': fav, 'homePrice': h_price, 'awayPrice': a_price,
            'over25Price': over, 'under25Price': under,
            'over25Probability': ((1/over)/(1/over+1/under)) if over and under else None,
            'source': source_url, 'sourceRow': row_number})
    if audit['validResults'] != LEAGUES[league][2]:
        raise ValueError(f'{season} {league}: expected {LEAGUES[league][2]} unique completed games, got {audit["validResults"]}')
    return parsed, dict(audit), rejected


def side_stats(rows, side):
    applicable = [r for r in rows if side in ('home', 'away') or r['line'] != 0]
    outcomes, profits = Counter(), []
    for r in applicable:
        selected = side if side in ('home', 'away') else (
            r['favorite'] if side == 'upper' else 'away' if r['favorite'] == 'home' else 'home')
        sign = 1 if selected == 'home' else -1
        result = r['homeSettlement'] * sign
        outcomes[OUTCOMES[result]] += 1
        p = r[selected+'Price']
        # Require both prices to reject incomplete paired market observations for the return comparison.
        if p and r['homePrice'] and r['awayPrice']:
            profits.append(profit((r['hg']-r['ag'])*sign, r['line']*sign, p))
    n = len(applicable)
    return {'n': n, 'outcomes': {k: outcomes[k] for k in OUTCOMES.values()},
            'positive': proportion(outcomes['全赢']+outcomes['赢半'], n),
            'pricedN': len(profits), 'profitPer100': round(sum(profits)*100, 2),
            'roiPct': round(sum(profits)/len(profits)*100, 2) if profits else None}


def summary(rows):
    n = len(rows)
    scores = Counter(f'{r["hg"]}:{r["ag"]}' for r in rows)
    fav_scores = Counter(f'{r["hg"]}:{r["ag"]}' if r['favorite'] == 'home' else f'{r["ag"]}:{r["hg"]}'
                         for r in rows if r['favorite'])
    margins = Counter(r['hg']-r['ag'] for r in rows)
    half = [r for r in rows if abs(r['line']) == .5]
    lower_wins = [r for r in half if r['homeSettlement'] * (1 if r['favorite'] == 'home' else -1) < 0]
    def score_rows(c, total):
        return [{'score': s, 'count': k, 'pct': ratio(k, total)}
                for s, k in sorted(c.items(), key=lambda x: (-x[1], x[0]))[:8]]
    return {'n': n,
        'bands': {str(limit): proportion(sum(r['distance'] <= limit for r in rows), n) for limit in [.5, 1, 2]},
        'draw': proportion(sum(r['hg'] == r['ag'] for r in rows), n),
        'homeWin': proportion(sum(r['hg'] > r['ag'] for r in rows), n),
        'awayWin': proportion(sum(r['hg'] < r['ag'] for r in rows), n),
        'oneGoalOrDraw': proportion(sum(abs(r['hg']-r['ag']) <= 1 for r in rows), n),
        'under25': proportion(sum(r['hg']+r['ag'] <= 2 for r in rows), n),
        'draw00or11': proportion(sum(r['hg'] == r['ag'] and r['hg'] <= 1 for r in rows), n),
        'meanDistance': round(sum(r['distance'] for r in rows)/n, 3) if n else None,
        'homeScores': score_rows(scores, n), 'favoriteScores': score_rows(fav_scores, sum(fav_scores.values())),
        'marginDistribution': [{'margin': m, 'count': k} for m, k in sorted(margins.items())],
        'sides': {side: side_stats(rows, side) for side in ['home', 'away', 'upper', 'lower']},
        'halfBall': {'n': len(half), 'lowerWin': proportion(len(lower_wins), len(half)),
            'fixed00or11': proportion(sum(r['hg']==r['ag'] and r['hg'] <= 1 for r in half), len(half)),
            'drawGivenLowerWin': proportion(sum(r['hg']==r['ag'] for r in lower_wins), len(lower_wins)),
            'draw00or11GivenLowerWin': proportion(sum(r['hg']==r['ag'] and r['hg'] <= 1 for r in lower_wins), len(lower_wins)),
            'underdogOutrightWins': sum(r['hg'] != r['ag'] for r in lower_wins),
            'otherDraws': sum(r['hg']==r['ag'] and r['hg'] >= 2 for r in lower_wins)}}


def group(rows):
    def compact(selected, keys):
        stats = summary(selected)
        return {k: stats[k] for k in ['n', *keys]}
    return {'summary': summary(rows),
        'byLine': [{'line': line, **compact([r for r in rows if r['line']==line],
            ['draw', 'homeWin', 'awayWin', 'bands', 'draw00or11'])} for line in [-.5, -.25, 0, .25, .5]],
        'byDepth': [{'depth': depth, **compact([r for r in rows if abs(r['line'])==depth],
            ['draw', 'under25', 'bands', 'draw00or11', 'sides'])} for depth in [0, .25, .5]],
        'byMovement': [{'movement': m, **compact([r for r in rows if r['movement']==m],
            ['draw', 'bands', 'under25', 'sides'])}
                       for m in ['让球加深', '让球变浅', '让受互换', '退至平手', '盘口不变', '无可比早盘']],
        'byTotalMarket': [{'market': label, **compact([r for r in rows if pred(r['over25Probability'])],
            ['under25', 'draw', 'draw00or11'])}
            for label, pred in [('偏小球', lambda p: p is not None and p < .45),
                                ('均衡', lambda p: p is not None and .45 <= p <= .55),
                                ('偏大球', lambda p: p is not None and p > .55),
                                ('无成对大小球报价', lambda p: p is None)] ]}


def source_file(archive, season, league, refresh=False):
    code = season[2:4] + season[-2:]
    url = f'{SOURCE}mmz4281/{code}/{LEAGUES[league][1]}.csv'
    path = archive / season / f'{league}.csv'
    receipt = path.with_suffix('.receipt.json')
    if refresh or not path.exists():
        with urlopen(Request(url, headers={'User-Agent': 'FengyiHistoricalResearch/1.0'}), timeout=40) as response:
            raw = response.read(2_000_000)
            assert len(raw) < 2_000_000
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
        receipt.write_text(json.dumps({'url': url, 'retrievedAt': datetime.now(timezone.utc).isoformat(),
            'sha256': hashlib.sha256(raw).hexdigest()}, indent=2), encoding='utf-8')
    raw = path.read_bytes()
    meta = json.loads(receipt.read_text(encoding='utf-8'))
    assert meta['url'] == url and meta['sha256'] == hashlib.sha256(raw).hexdigest()
    rows, audit, rejected = parse(raw, season, league, url)
    return rows, {**meta, 'season': season, 'league': league, 'audit': audit, 'rejected': rejected}


def export_csv(path, rows):
    header = ['赛季', '联赛', '日期', '主队', '客队', '主队进球', '客队进球', '赛前收盘主队让球',
              '较早采样主队让球_非正式初盘', '盘口变化', '主队净胜球', '净胜球与盘口中心距离',
              '主队亚洲盘结算', '让球方', 'Bet365收盘主水_十进制', 'Bet365收盘客水_十进制',
              'Bet365收盘大2.5', 'Bet365收盘小2.5', '来源', '来源CSV行号']
    with path.open('w', encoding='utf-8-sig', newline='') as f:
        w = csv.writer(f); w.writerow(header)
        for r in sorted(rows, key=lambda r: (r['date'], r['league'], r['home'])):
            # Team names are source facts, never spreadsheet expressions.
            safe = lambda s: "'"+s if s and s[0] in '=+-@' else s
            w.writerow([r['season'], LEAGUES[r['league']][0], r['date'], safe(r['home']), safe(r['away']),
                r['hg'], r['ag'], r['line'], r['earlyLine'], r['movement'], r['hg']-r['ag'], r['distance'],
                OUTCOMES[r['homeSettlement']], '主队' if r['favorite']=='home' else '客队' if r['favorite']=='away' else '平手无上下盘',
                r['homePrice'], r['awayPrice'], r['over25Price'], r['under25Price'], r['source'], r['sourceRow']])


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--archive', type=Path, required=True)
    p.add_argument('--public-output', type=Path, required=True)
    p.add_argument('--refresh', action='store_true')
    args = p.parse_args()
    args.archive.mkdir(parents=True, exist_ok=True)
    args.public_output.mkdir(parents=True, exist_ok=True)
    all_rows, sources, seasons = [], [], []
    for season in SEASONS:
        with ThreadPoolExecutor(max_workers=4) as pool:
            results = list(pool.map(lambda league: source_file(args.archive/'source', season, league, args.refresh), LEAGUES))
        rows = [r for records, _ in results for r in records]
        receipts = [m for _, m in results]
        all_rows.extend(rows); sources.extend(receipts)
        seasons.append({'season': season, **group(rows), 'leagues': [
            {'id': lid, 'label': cfg[0], **group([r for r in rows if r['league']==lid])} for lid, cfg in LEAGUES.items()]})
        export_csv(args.archive/f'{season}-半球以内逐场记录.csv', rows)
        print(json.dumps({'season': season, 'n': len(rows), 'byLeague': {m['league']: m['audit'] for m in receipts}}, ensure_ascii=False), flush=True)
    report = {'version': VERSION, 'generatedAt': datetime.now(timezone.utc).isoformat(),
        'basis': {'field': 'AHCh', 'scope': '平手、平半、半球，主队让球及受让均纳入',
            'closing': '数据源标注的赛前收盘；未提供精确采样时分，不代表逐秒确认的开赛前最后一笔',
            'distance': 'abs(主队进球 - 客队进球 + 主队收盘让球)',
            'result': '常规比赛时间（含补时）；不含加时和点球大战',
            'sampling': '较早采样 AHh 仅用于变盘分组，不称为正式初盘；未变盘不等于水位未变',
            'returns': '每场固定100单位，按Bet365成对收盘十进制赔率；不等于网站实际推荐收益',
            'interpretation': '历史描述性研究，不计入赛前预测命中率；同样本高频比分含事后选择，不等于下一场命中率',
            'intervals': 'Wilson 95%区间，仅衡量样本比例抽样波动；同球队重复出赛等相关性未建模',
            'selection': '固定以收盘盘口绝对值不超过0.5筛选；缺失或无效收盘盘口不使用其他时点替代'},
        'sources': sources, 'notesUrl': SOURCE+'notes.txt', 'sourceUrl': SOURCE+'data.php',
        'all': {**group(all_rows), 'leagues': [{'id': lid, 'label': cfg[0], **group([r for r in all_rows if r['league']==lid])} for lid, cfg in LEAGUES.items()]},
        'seasons': seasons}
    (args.public_output/'shallow-handicap.json').write_text(json.dumps(report, ensure_ascii=False, separators=(',', ':')), encoding='utf-8')
    (args.archive/'研究汇总.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    export_csv(args.archive/'三季四大联赛-半球以内逐场记录.csv', all_rows)
    print(json.dumps({'all': report['all']['summary']}, ensure_ascii=False), flush=True)


if __name__ == '__main__':
    main()
