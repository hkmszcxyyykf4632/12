"""Read the full forecast ledger; never generate forecasts while measuring them."""
import json
import math
import sqlite3
from contextlib import closing
from datetime import datetime, timedelta, timezone
from typing import Final

from pydantic import ValidationError

from .files import PUBLIC, STATE
from .football_rounds import RoundEntry, round_info
from .football_forecasts import identity, settlement
from .match_centre_research import same_fixture
from .match_details import match_catalogue
from .match_research import load
from .motivation import digest, dt
from .statistics_models import FootballReceipt, FootballReport, FootballSnapshot, Statistics

LEAGUES: Final = {'700': 'epl', '740': 'laliga', '730': 'seriea', '720': 'bundesliga', '775': 'ucl'}
HK: Final = timezone(timedelta(hours=8))


def read_statistics() -> Statistics:
    """All saved stages, including matches outside the rolling daily feed."""
    at = datetime.now(timezone.utc)
    path = STATE / 'football-forecasts.sqlite3'
    if not path.exists():
        return Statistics(updatedAt=at, records=[])
    with closing(sqlite3.connect(path.as_uri() + '?mode=ro', uri=True)) as db:
        db.row_factory = sqlite3.Row
        saved = db.execute('SELECT * FROM forecasts ORDER BY issued_at DESC').fetchall()
    daily = {r['id']: r for r in load(PUBLIC / 'daily-football.json').get('matches', [])}
    rounds = []
    for entry in load(PUBLIC / 'football-rounds.json').get('records', []):
        try:
            rounds.append(RoundEntry.model_validate(entry))
        except ValidationError:
            continue
    catalogues, records, unreadable = {}, [], 0
    for stored in saved:
        try:
            raw = json.loads(stored['snapshot'])
            snapshot = FootballSnapshot.model_validate(raw)
            report = FootballReport.model_validate_json(stored['content'])
            row = raw['match']
            fixture = snapshot.match
            league = LEAGUES.get(fixture.competitionId)
            if not league:
                continue
            if set(fixture.teams) != {'home', 'away'}:
                unreadable += 1
                continue
            reason = ''
            if (stored['identity'] != identity(row) or stored['event_id'] != fixture.id
                    or stored['stage'] != report.stage or dt(stored['issued_at']) != report.issuedAt
                    or digest(raw) != report.snapshotHash):
                reason = '封存身份或校验不一致'
            if (report.issuedAt >= fixture.kickoff or snapshot.capturedAt > report.issuedAt
                    or fixture.started or fixture.finished or fixture.state != 'scheduled'):
                reason = '未通过赛前时间与状态核对'
            home, away = fixture.teams['home'], fixture.teams['away']
            receipt = FootballReceipt(identity=stored['identity'], eventId=fixture.id, league=league,
                kickoff=fixture.kickoff, day=fixture.kickoff.astimezone(HK).date().isoformat(),
                home=home.label or home.name, away=away.label or away.name,
                homeName=home.name, awayName=away.name, stage=report.stage, issuedAt=report.issuedAt,
                score=report.score, asianSide=report.asianSide, source=fixture.source)
            season, round_label, round_source, complete = round_info(league, home.name, away.name, fixture.kickoff, rounds)
            receipt = receipt.model_copy(update={'season': season, 'round': round_label, 'roundSource': round_source, 'roundComplete': complete})
            if reason:
                records.append(receipt.model_copy(update={'status': 'excluded', 'reason': reason}))
                continue
            if league not in catalogues:
                try:
                    catalogues[league] = match_catalogue(league)[1]
                except (OSError, ValueError, KeyError):
                    catalogues[league] = []
            matches = [m for m in catalogues[league] if same_fixture({**row, 'league': league}, m, league)]
            current = daily.get(fixture.id)
            if current and identity(current) != stored['identity']:
                records.append(receipt.model_copy(update={'status': 'excluded', 'reason': '赛程时间或对手已改变，旧预测另列'}))
                continue
            result = current or row
            match = matches[0] if len(matches) == 1 else None
            if match:
                receipt = receipt.model_copy(update={'matchId': match['id']})
            if result.get('state') in {'cancelled', 'postponed', 'abandoned'}:
                records.append(receipt.model_copy(update={'status': 'void', 'reason': '取消、延期或中断'}))
                continue
            score = tuple(result.get('teams', {}).get(s, {}).get('goals') for s in ('home', 'away'))
            scope, finished = result.get('scoreScope', ''), result.get('state') == 'finished' and result.get('finished')
            if match and match.get('finished') and not match.get('provisional'):
                score = (match.get('homeGoals'), match.get('awayGoals'))
                scope, finished = match.get('scoreScope', ''), True
                receipt = receipt.model_copy(update={'source': match.get('source') or receipt.source})
            quote = report.quote or {}
            line, stamp = quote.get('line'), dt(quote.get('fetchedAt'))
            valid_quote = (type(line) in (int, float) and math.isfinite(line) and abs(line) <= 10
                           and abs(line * 4 - round(line * 4)) < 1e-8 and stamp is not None
                           and stamp <= report.issuedAt < fixture.kickoff and not quote.get('inPlay')
                           and quote.get('market') == 'asian-handicap' and bool(quote.get('source')))
            if valid_quote:
                receipt = receipt.model_copy(update={'line': float(line), 'provider': str(quote.get('provider') or ''),
                                                       'quoteAt': stamp.isoformat()})
            prices = quote.get('prices')
            price = prices.get(report.asianSide) if isinstance(prices, dict) else None
            if valid_quote and type(price) in (int, float) and math.isfinite(price) and 1 < price <= 10000:
                receipt = receipt.model_copy(update={'asianPrice': float(price)})
            correct_score = []
            for q in row.get('quotes', []):
                if not isinstance(q, dict):
                    continue
                captured = dt(q.get('fetchedAt'))
                prices = q.get('prices')
                value = prices.get(':'.join(str(n) for n in report.score)) if isinstance(prices, dict) else None
                if (q.get('market') == 'correct-score' and captured and captured <= snapshot.capturedAt
                        and not q.get('inPlay') and q.get('source')
                        and q.get('phase') in {'latest', 'opening', 'preclosing', 'closing'}
                        and type(value) in (int, float) and math.isfinite(value) and 1 < value <= 10000):
                    correct_score.append((captured, value, q))
            if correct_score:
                captured, value, q = max(correct_score, key=lambda item: item[0])
                receipt = receipt.model_copy(update={'scorePrice': float(value), 'scoreQuoteAt': captured.isoformat(),
                    'scoreProvider': str(q.get('provider') or ''), 'scoreSource': str(q['source'])})
            if finished and scope.replace(' ', '') == '90分钟含补时' and all(type(n) is int and n >= 0 for n in score):
                ah = 'unselected' if report.asianSide == 'pass' else 'unverified'
                if report.asianSide != 'pass' and valid_quote:
                    ah = settlement(score, line, report.asianSide)
                receipt = receipt.model_copy(update={'status': 'settled', 'actual': score,
                    'exactHit': score == report.score,
                    'resultHit': ((score[0] > score[1]) - (score[0] < score[1])) ==
                                 ((report.score[0] > report.score[1]) - (report.score[0] < report.score[1])),
                    'asianResult': ah})
            records.append(receipt)
        except (ValidationError, ValueError, KeyError, TypeError):
            unreadable += 1
    return Statistics(updatedAt=at, records=records, unreadable=unreadable)
