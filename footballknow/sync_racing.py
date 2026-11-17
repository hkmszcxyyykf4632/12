import sys

from football.racing import sync_catalogue, sync_meetings, warm_profiles
from football.horse_directory import sync_directory
from football.racing_people import sync_people
from football.racing_live import sync_live_racing

if __name__ == '__main__':
    kind = sys.argv[1] if len(sys.argv) > 1 else 'meetings'
    task = {'meetings': sync_meetings, 'catalogue': sync_catalogue, 'horses': warm_profiles,
            'directory': sync_directory, 'people': sync_people, 'live': sync_live_racing}[kind]
    print(f'Hong Kong racing {kind}: {task()} updated')
