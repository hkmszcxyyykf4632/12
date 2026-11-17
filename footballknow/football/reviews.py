"""Immutable analysis snapshots and separately dated outcome reviews."""
import hashlib
import json
import math
import threading
from datetime import datetime, time, timezone

from pydantic import BaseModel, ConfigDict, Field

from .files import STATE, publish
from .finance import FOLDER, HK, load, now, stock
from .professional_prompts import professional_rules, VERSION
from .text_ai import request_json

LOCK = threading.Lock()
OUTPUT = '''本次任务是复盘或市场研究，不重新发布原预测。只输出 JSON：{"summary":["结论第一段","结论第二段"],"details":[{"title":"依据","text":"可核实资料"}]}。摘要 2 至 3 段，每段最多 240 字；详细资料 1 至 5 项，标题不超过 40 字、正文不超过 900 字。复盘先对照不可修改的原预测与事实，再简述得到支持及失准的依据；没有原文时明确没有原文。没有到期的预测只能写观察中。'''


class Detail(BaseModel):
    model_config = ConfigDict(extra='forbid')
    title: str = Field(min_length=1, max_length=40)
    text: str = Field(min_length=1, max_length=900)


class ReviewContent(BaseModel):
    model_config = ConfigDict(extra='forbid')
    summary: list[str] = Field(min_length=2, max_length=3)
    details: list[Detail] = Field(min_length=1, max_length=5)


def watched_codes():
    return load(STATE / 'stock-watchlist.json').get('codes', [])


def save_watchlist(codes):
    values = sorted(set(codes))
    if len(values) > 200 or any(not stock(code) for code in values):
        raise ValueError('关注名单包含未知股票，或超过 200 只。')
    result = {'codes': values, 'updatedAt': now()}
    publish(STATE / 'stock-watchlist.json', result)
    return result


def require_watched(code):
    if code not in watched_codes():
        raise ValueError('请先把这只股票加入我的关注，再进行分析或复盘。')


def path_for(domain, identity):
    key = hashlib.sha256(identity.encode()).hexdigest()
    return STATE / 'reviews' / domain / (key + '.json')


def report(domain, identity, context, generate=False):
    path = path_for(domain, identity)
    cached = load(path)
    if cached or not generate:
        return cached or None
    if not LOCK.acquire(blocking=False):
        raise ValueError('正在整理另一份复盘，请稍后重试。')
    try:
        cached = load(path)
        if cached:
            return cached
        content = ReviewContent.model_validate(request_json(professional_rules(domain, OUTPUT), context, 4500))
        content.summary = [' '.join(p.split()) for p in content.summary]
        if any(not p or len(p) > 240 for p in content.summary):
            raise ValueError('复盘摘要格式不正确，请稍后重试。')
        result = {**content.model_dump(), 'generatedAt': now(), 'protocolVersion': VERSION,
                  'snapshotHash': hashlib.sha256(json.dumps(context, ensure_ascii=False, sort_keys=True).encode()).hexdigest()}
        path.parent.mkdir(parents=True, exist_ok=True)
        try:
            with path.open('x', encoding='utf-8') as handle:
                path.chmod(0o600)
                json.dump(result, handle, ensure_ascii=False)
        except FileExistsError:
            return load(path)
        return result
    finally:
        LOCK.release()


def football_review(match_id, league='epl', generate=False):
    from .analysis import load_archive
    from .evaluation import Forecast, outcome
    from .leagues import league_path, league_config
    from .match_details import get_detail
    archive, _ = load_archive(league)
    match = next((m for m in archive.matches if m.id == match_id and m.competition == league_config(league).competition), None)
    if match is None:
        raise LookupError('比赛不存在。')
    identity = match.id if league == 'ucl' else f'{match.season}|{match.home}|{match.away}'
    key = hashlib.sha256(identity.encode()).hexdigest()
    original = load(league_path(STATE, league) / 'forecasts' / (key + '.json'))
    if original:
        f = Forecast.model_validate(original)
        issued = datetime.fromisoformat(f.generatedAt.replace('Z', '+00:00'))
        kickoff = datetime.fromisoformat(f.kickoff.replace('Z', '+00:00'))
        if f.league != league or issued.tzinfo is None or kickoff.tzinfo is None or issued >= kickoff:
            original = None
    completed = (match.finished and match.homeGoals is not None and match.awayGoals is not None
                 and not any(word in match.scoreScope for word in ('加时', '点球', 'aggregate')))
    actual = outcome(match) if completed else None
    result = {'original': original, 'finished': bool(completed), 'actual': actual,
              'correct': original['pick'] == actual if original and completed else None,
              'score': [match.homeGoals, match.awayGoals] if completed else None, 'review': None}
    if not completed:
        if generate:
            raise ValueError('比赛尚未完场，暂不能生成赛后复盘。')
        return result
    if not original:
        if generate:
            raise ValueError('这场比赛没有保存的赛前预测，不能补写预测复盘。')
        return result
    try:
        detail = get_detail(match.id, league, fetch_missing=False)
    except (OSError, ValueError, LookupError):
        detail = None
    if hasattr(detail, 'model_dump'):
        detail = detail.model_dump(mode='json')
    context = {'task': '赛前分析的赛后复盘', 'originalPrediction': original,
               'match': match.model_dump(mode='json'), 'result': result.copy(), 'matchDetails': detail,
               'checkedAt': now(), 'scoring': '90 分钟含补时胜平负；原首选固定，赛后资料只用于复盘。'}
    review_id = league + '|' + identity + '|' + str(result['score']) + '|' + original['generatedAt']
    result['review'] = report('football', review_id, context, generate)
    return result


def closed_bars(history, at):
    local = at.astimezone(HK)
    try:
        updated = datetime.fromisoformat(history.get('updatedAt', '')).astimezone(HK)
    except ValueError:
        updated = None
    cutoff = time(16, 15)
    today = local.date().isoformat()
    current_complete = local.time() >= cutoff and updated and updated.date() == local.date() and updated.time() >= cutoff
    return sorted([b for b in history.get('bars', [])
                   if isinstance(b.get('adjustedClose'), (int, float)) and math.isfinite(b['adjustedClose']) and b['adjustedClose'] > 0
                   and (b.get('date', '') < today or (b.get('date') == today and current_complete))], key=lambda b: b['date'])


def stock_review(code, generate=False, at=None):
    from .stock_analysis import public_status
    if not stock(code):
        raise LookupError('股票不存在。')
    if generate:
        require_watched(code)
    at = at or datetime.now(timezone.utc)
    history = load(FOLDER / 'history' / (code + '.json'))
    bars = closed_bars(history, at)
    base = {'code': code, 'review': None, 'original': None, 'close': None, 'watching': code in watched_codes()}
    if not bars:
        return {**base, 'message': '尚无已确认的收盘资料。'}
    close = bars[-1]
    close_at = datetime.combine(datetime.fromisoformat(close['date']).date(), time(16, 15), HK)
    forecasts = public_status(code)['forecasts']
    original = next((f for f in forecasts if datetime.fromisoformat(f['issuedAt']) < close_at), None)
    if not original:
        return {**base, 'message': '此收盘之前没有保存的预测；下一次符合条件的收盘后再复盘。'}
    issued_day = datetime.fromisoformat(original['issuedAt']).astimezone(HK).date().isoformat()
    eligible = [b for b in bars if b['date'] > issued_day]
    results = {}
    for horizon, sessions, threshold in [('week', 5, .01), ('quarter', 63, .05)]:
        ready = len(eligible) > sessions
        change = eligible[sessions]['adjustedClose'] / eligible[0]['adjustedClose'] - 1 if ready else None
        actual = ('up' if change > threshold else 'down' if change < -threshold else 'flat') if ready else None
        results[horizon] = {'status': '已到期' if ready else '观察中', 'completedSessions': max(0, len(eligible) - 1),
                            'requiredSessions': sessions, 'correct': original[horizon] == actual if ready else None,
                            'return': change, 'actual': actual}
    daily = close['adjustedClose'] / bars[-2]['adjustedClose'] - 1 if len(bars) > 1 else None
    result = {**base, 'original': original, 'close': close, 'dailyReturn': daily, 'outcomes': results,
              'priceSource': history.get('source'), 'priceUpdatedAt': history.get('updatedAt'),
              'message': '原预测保持不变，未到期的期限继续观察。'}
    identity = code + '|' + close['date'] + '|' + str(original['id'])
    result['review'] = report('stocks', identity, {'task': '收盘后对先前预测复盘', **result}, generate)
    return result


def refresh_watched_reviews():
    """One watched stock per worker invocation, only after the market close."""
    from .finance import refresh_history
    from .sync_control import read_control
    at = datetime.now(timezone.utc).astimezone(HK)
    if at.weekday() >= 5 or at.time() < time(16, 20) or not read_control()['enabled']:
        return {'generated': 0}
    attempts_path = STATE / 'stock-review-checks.json'
    attempts = load(attempts_path)
    for code in watched_codes():
        checked = attempts.get(code)
        if checked and (at - datetime.fromisoformat(checked)).total_seconds() < 600:
            continue
        existing = stock_review(code)
        from .stock_analysis import public_status
        if not public_status(code)['latest'] or ((existing.get('close') or {}).get('date') == at.date().isoformat() and existing.get('review')):
            continue
        attempts[code] = at.isoformat()
        publish(attempts_path, attempts)
        refresh_history(code)
        pending = stock_review(code)
        if (pending.get('close') or {}).get('date') != at.date().isoformat() or pending.get('review'):
            return {'generated': 0, 'checked': 1}
        stock_review(code, generate=True)
        return {'generated': 1}
    return {'generated': 0}


def asset_review(ident, generate=False):
    domain = {'gold': 'gold', 'wti': 'oil', 'brent': 'oil', 'bitcoin': 'crypto'}.get(ident)
    asset = load(FOLDER / 'assets.json').get('assets', {}).get(ident)
    if not domain or not asset:
        raise LookupError('市场品种暂未提供。')
    # The first analysis of each UTC day is fixed, with its own source timestamp.
    identity = ident + '|' + datetime.now(timezone.utc).date().isoformat()
    context = {'task': '市场品种研究', 'asset': asset, 'asOf': now(),
               'dollarAndMarkets': load(FOLDER / 'global-markets.json'), 'policyRates': load(FOLDER / 'policy-rates.json')}
    return {'asset': ident, 'report': report(domain, identity, context, generate)}
