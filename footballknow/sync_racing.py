import argparse
import json

from football.racing import sync_catalogue, sync_meetings, warm_profiles
from football.horse_directory import sync_directory
from football.racing_people import sync_people
from football.racing_live import sync_live_racing
from football.racing_analysis import sync_forecasts

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('kind', nargs='?', default='meetings', choices=['meetings', 'catalogue', 'horses', 'directory', 'people', 'live', 'forecasts'])
    parser.add_argument('--date', help='Hong Kong race date (YYYY-MM-DD), forecasts only')
    parser.add_argument('--limit', type=int, default=2, help='Maximum forecasts attempted per run')
    args = parser.parse_args()
    kind = args.kind
    if kind == 'forecasts':
        result = sync_forecasts(args.date, args.limit)
        print(json.dumps(result, ensure_ascii=False))
        raise SystemExit(1 if result['failed'] else 0)
    task = {'meetings': sync_meetings, 'catalogue': sync_catalogue, 'horses': warm_profiles,
            'directory': sync_directory, 'people': sync_people, 'live': sync_live_racing}[kind]
    print(f'Hong Kong racing {kind}: {task()} updated')
