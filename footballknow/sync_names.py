"""Populate verified Mandarin and Hong Kong player-name variants."""
import sys

from football.names import refresh_names
from football.name_rosters import refresh_club_names

if __name__ == '__main__':
    if '--rosters-only' not in sys.argv:
        refresh_names(1000 if '--full' in sys.argv else 60)
    snapshot = refresh_club_names()
    print(f'Names: {snapshot.total - len(snapshot.unresolved)}/{snapshot.total} current players matched')
