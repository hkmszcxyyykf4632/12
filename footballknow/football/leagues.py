"""Known league identifiers; storage never accepts arbitrary path components."""
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

LeagueId = Literal['epl', 'laliga', 'ucl', 'seriea', 'bundesliga']


@dataclass(frozen=True)
class League:
    id: str
    competition: str
    lower: str


LEAGUES = {'epl': League('epl', '英超', '英冠'), 'laliga': League('laliga', '西甲', '西乙'),
           'ucl': League('ucl', '欧冠', '其他正式赛事'),
           'seriea': League('seriea', '意甲', '意乙'),
           'bundesliga': League('bundesliga', '德甲', '德乙')}


def league_config(league: str = 'epl') -> League:
    if league not in LEAGUES:
        raise ValueError('Unknown league')
    return LEAGUES[league]


def league_path(root: Path, league: str = 'epl') -> Path:
    config = league_config(league)
    return root if config.id == 'epl' else root / config.id
