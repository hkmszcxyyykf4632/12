"""Public, idempotent production queue derived only from frozen recommendations."""
import json
from datetime import datetime, timezone

from .files import PUBLIC, publish
from .match_research import load
from .motivation import digest, dt


def refresh_queue(records, at=None):
    at = at or datetime.now(timezone.utc)
    published = load(PUBLIC / 'media/recommendation-videos.json').get('videos', [])
    done = {v.get('event') for v in published if v.get('url') and v.get('poster')}
    jobs = []
    for record in records:
        receipt = record.get('receipt', {})
        if record['event'] in done or receipt.get('status') != 'pending' or not at < dt(record['kickoff']):
            continue
        if record['domain'] != 'football':
            continue
        side = receipt.get('asianSide')
        if side not in ('H', 'A') or receipt.get('line') is None:
            continue
        home, away = receipt['home'], receipt['away']
        pick = home if side == 'H' else away
        line = receipt['line']
        amount = {0.25: '平手半球', 0.5: '半球', 0.75: '半球一球', 1: '一球',
                  1.25: '一球球半', 1.5: '一球半', 1.75: '球半两球', 2: '两球', 2.5: '两球半'}.get(abs(line), f'{abs(line):g}球')
        handicap = f'{home}和{away}平手啊。' if line == 0 else f'{home if line < 0 else away}让{away if line < 0 else home}{amount}啊。'
        scores = receipt.get('scoreCandidates') or [receipt['score']]
        numbers = '零一二三四五六七八九十'
        score_text = '，或者'.join('比'.join(numbers[n] if n <= 10 else str(n) for n in score) for score in scores)
        jobs.append({'id': digest([record['event'], record['issuedAt'], record['stage']]),
            'event': record['event'], 'domain': 'football', 'group': record['group'],
            'stage': record['stage'], 'issuedAt': record['issuedAt'], 'kickoff': record['kickoff'],
            'title': f'{home} 对 {away} · {pick}', 'pick': pick,
            'source': receipt.get('source'), 'quoteAt': receipt.get('quoteAt'), 'receipt': receipt,
            'summary': record.get('summary', []), 'status': 'queued',
            'dialogue': ['喂，今晚有什么好料啊？', f'今晚买{pick}啊。', '怎么让啊？', handicap,
                         '买几比几啊？', score_text + '啊。', '为什么买它啊？'],
            'reasonInstruction': '补第八句：只用封存预测中的可核对变盘或往绩事实，简短自然，最后加啊；不把未知变盘原因说成事实。',
            'visualReference': 'original-characters-v3', 'voiceReference': 'approved-football-dialogue',
            'instructions': '沿用已认可两只公仔、背景和声音参考。实际生成后核对队名、盘口、两个比分、配音、画面；开赛后不可发布成赛前推荐。'})
    result = {'updatedAt': at.isoformat(), 'jobs': sorted(jobs, key=lambda j: (j['kickoff'], j['id'])),
              'method': '文字推荐自动发布后进入制作队列；视频生成及核对完成才显示。队列不代表视频已完成。'}
    publish(PUBLIC / 'recommendation-video-queue.json', result)
    return result
