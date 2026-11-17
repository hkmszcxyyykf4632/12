import sys

from football.racing import sync_catalogue, sync_meetings, warm_profiles

if __name__ == '__main__':
    kind = sys.argv[1] if len(sys.argv) > 1 else 'meetings'
    task = {'meetings': sync_meetings, 'catalogue': sync_catalogue, 'horses': warm_profiles}[kind]
    print(f'Hong Kong racing {kind}: {task()} updated')
