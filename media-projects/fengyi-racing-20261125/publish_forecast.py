"""Publish this audited pre-race note through the normal cutoff and snapshot checks."""
import json
from pathlib import Path
import sys
from football import racing_analysis, recommendations
from football.recommendation_candidates import racing_candidates
from datetime import datetime, timezone

race_id = '2026-11-25-HV-7'
prepared = json.loads(Path(sys.argv[1]).read_text(encoding='utf-8'))
race = racing_analysis.get_race(race_id)
entries = {str(h['number']): h for h in race['entries']}
assert race['date'] == '2026-11-25' and race['distance'] == 1200
assert entries['8']['id'] == 'HK_2024_K239' and int(entries['8']['draw']) == 1
assert entries['1']['id'] == 'HK_2024_K275' and entries['9']['id'] == 'HK_2024_K228'
assert not any(entries[n].get('withdrawn') for n in ['8','1','9'])
report = racing_analysis.generate(race_id, 'pre', prepared_content=prepared,
    prepared_by='Codex 核对稿 · 2026-11-24')['reports']['pre']
assert report['pick'] == prepared['pick'] and report['summary'] == prepared['summary']
at = datetime.now(timezone.utc)
candidates = [c for c in racing_candidates(at) if c.event == race_id]
assert len(candidates) == 1, 'Reviewed report did not pass selection eligibility'
added = recommendations.publish_candidates(candidates, at)
selected = [r for r in recommendations.read_recommendations()['records'] if r['event'] == race_id]
assert len(selected) == 1 and selected[0]['receipt']['pick'] == prepared['pick']
print(json.dumps({'raceId':race_id,'issuedAt':report['issuedAt'],
    'publishedAt':selected[0]['publishedAt'],'newSelection':added,'pick':report['pick']},ensure_ascii=False))

