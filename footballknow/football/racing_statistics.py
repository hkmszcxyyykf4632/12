"""Settle the original shortlist against official dividends, including dead heats."""
import itertools
import re
import sqlite3
from contextlib import closing
from datetime import datetime, timezone
from typing import Final

from pydantic import ValidationError

from .files import STATE
from .motivation import dt
from .match_research import load
from .racing import FOLDER
from .statistics_models import Dividend, PoolReceipt, Race, RacingReceipt, RacingReport, Runner, Statistics, Ticket

POOLS: Final = ('WIN', 'PLA', 'QIN', 'QPL')


def combination(value: str) -> str:
    """Normalize official numeric combinations without treating a refund as a winner."""
    bits = re.split(r'[,，+\s]+', value.strip())
    if not bits or any(not re.fullmatch(r'\d{1,2}', bit) for bit in bits):
        return ''
    return ','.join(str(n) for n in sorted(int(bit) for bit in bits))


def settle_pool(kind: str, selected: list[str], withdrawn: set[str], dividends: list[Dividend], official: bool) -> PoolReceipt:
    """One unit per horse, or each unordered pair. Missing payouts remain pending."""
    pairs = kind in {'QIN', 'QPL'}
    tickets = list(itertools.combinations(selected, 2 if pairs else 1))
    payouts = [d for d in dividends if d.type == kind]
    all_refund = any(('退' in d.display or 'REFUND' in d.display.upper()) and not combination(d.combination) for d in payouts)
    winners = {combination(d.combination): d for d in payouts if combination(d.combination)}
    complete = bool(winners) and all(d.amount is not None and d.amount > 0 for d in winners.values())
    result = []
    for ticket in tickets:
        key = combination(','.join(ticket))
        if any(n in withdrawn for n in ticket) or official and all_refund:
            result.append(Ticket(combination=key, status='refund', dividend=10, multiple=1))
            continue
        payout = winners.get(key)
        if not official or not complete:
            result.append(Ticket(combination=key, status='pending'))
        elif payout:
            result.append(Ticket(combination=key, status='hit', dividend=round(payout.amount / payout.unit * 10, 4),
                                 multiple=round(payout.amount / payout.unit, 6)))
        else:
            result.append(Ticket(combination=key, status='miss', dividend=0, multiple=0))
    return PoolReceipt(type=kind, tickets=result)


def read_statistics() -> Statistics:
    """Read every saved pre-race report, retaining cancelled and unresolved races."""
    at = datetime.now(timezone.utc)
    path = STATE / 'racing-analysis.sqlite3'
    if not path.exists():
        return Statistics(updatedAt=at, records=[])
    with closing(sqlite3.connect(path.as_uri() + '?mode=ro', uri=True)) as db:
        db.row_factory = sqlite3.Row
        rows = db.execute("SELECT * FROM reports WHERE phase='pre' ORDER BY issued_at DESC").fetchall()
    completed = completed_meetings()
    records, unreadable = [], 0
    for stored in rows:
        ident = stored['race_id']
        if not re.fullmatch(r'\d{4}-\d{2}-\d{2}-(ST|HV)-\d{1,2}', ident):
            unreadable += 1
            continue
        try:
            report = RacingReport.model_validate_json(stored['content'])
            race = Race.model_validate_json((FOLDER / 'races' / (ident + '.json')).read_text('utf-8'))
            issued = dt(stored['issued_at'])
            if issued is None:
                unreadable += 1
                continue
            reason = ''
            original_off = dt(report.marketSnapshot.get('offTime'))
            original_id = report.marketSnapshot.get('raceId')
            effective_off = race.offTime or (original_off if race.status == 'cancelled' else None)
            if (not effective_off or issued >= effective_off or race.id != ident
                    or original_off and original_off != effective_off or original_id and original_id != ident):
                reason = '赛前时间或本场身份未能通过核对'
            entries = race.entries or (saved_runners(report) if race.status == 'cancelled' else [])
            runners = [next((h for h in entries if h.id == horse_id), None) for horse_id in report.shortlist]
            if (len(set(report.shortlist)) != len(report.shortlist) or report.pick not in report.shortlist
                    or any(h is None for h in runners)):
                reason = '原推荐名单与出赛身份不一致'
            valid_runners = [h for h in runners if h is not None]
            selected = [combination(str(h.number)) for h in valid_runners]
            if len(set(selected)) != len(selected) or not all(selected):
                reason = '马号缺失或重复，不能核对派彩组合'
            withdrawn = {combination(str(h.number)) for h in valid_runners if h.withdrawn}
            official = race.status == 'finished' and race.resultOfficial
            status = 'settled' if official else 'pending'
            if race.status == 'cancelled':
                status = 'void'
                withdrawn = set(selected)
            if reason:
                status = 'excluded'
            pools = [settle_pool(kind, selected, withdrawn, race.dividends, official and not reason) for kind in POOLS]
            records.append(RacingReceipt(meetingComplete=(race.date, race.course) in completed, raceId=ident, day=race.date, course=race.course,
                courseName=race.courseName, raceNo=race.raceNo, issuedAt=issued, status=status,
                reason=reason, pick=report.pick, runners=valid_runners, pools=pools, source=race.source))
        except (OSError, ValidationError, ValueError, TypeError):
            unreadable += 1
    return Statistics(updatedAt=at, records=records, unreadable=unreadable)


def saved_runners(report: RacingReport) -> list[Runner]:
    if report.runnerSnapshot:
        return report.runnerSnapshot
    horses = {}
    pools = report.marketSnapshot.get('pools', [])
    if not isinstance(pools, list):
        return []
    for pool in pools:
        if not isinstance(pool, dict) or not isinstance(pool.get('quotes'), list):
            continue
        for quote in pool['quotes']:
            if not isinstance(quote, dict) or not isinstance(quote.get('horses'), list):
                continue
            for raw in quote['horses']:
                horse = Runner.model_validate(raw)
                horses[horse.id] = horse
    return list(horses.values())


def completed_meetings() -> set[tuple[str, str]]:
    groups = {}
    for row in load(FOLDER / 'meetings.json').get('races', []):
        ident = row.get('id', '')
        if not re.fullmatch(r'\d{4}-\d{2}-\d{2}-(ST|HV)-\d{1,2}', ident):
            continue
        detail = load(FOLDER / 'races' / (ident + '.json')) or row
        complete = detail.get('status') == 'cancelled' or (detail.get('status') == 'finished' and detail.get('resultOfficial') is True)
        groups.setdefault((row['date'], row['course']), []).append(complete)
    return {key for key, values in groups.items() if values and all(values)}
