"""Refresh the public EPL live fixture snapshot once."""
from football.live import refresh_live

if __name__ == '__main__':
    snapshot = refresh_live()
    print(f'Live fixtures refreshed: {len(snapshot.matches)}, fetched at {snapshot.updatedAt}')
