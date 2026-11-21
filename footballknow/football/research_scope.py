"""Competitions with scheduled football analysis; worldwide scores remain available."""
SUPPORTED_COMPETITIONS = {'700': '英超', '740': '西甲', '730': '意甲', '720': '德甲', '775': '欧冠'}
SUPPORTED_LEAGUES = {'epl', 'laliga', 'seriea', 'bundesliga', 'ucl'}


def supports_research(row):
    competition = str(row.get('competitionId') or '')
    return competition in SUPPORTED_COMPETITIONS if competition else row.get('league') in SUPPORTED_LEAGUES
