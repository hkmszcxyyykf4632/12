"""Refresh a single La Liga dataset without affecting Premier League jobs."""
import argparse
import json

from football.laliga import refresh_catalogue, refresh_laliga_live
from football.history import refresh_history
from football.names import refresh_names
from football.name_rosters import refresh_club_names


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('dataset', choices=['catalogue', 'live', 'history', 'names'])
    parser.add_argument('--full', action='store_true')
    args = parser.parse_args()
    if args.dataset == 'catalogue':
        result = refresh_catalogue()
        print(json.dumps({key: len(result[key]) for key in ['teams', 'players', 'matches']}, ensure_ascii=False))
    elif args.dataset == 'live':
        result = refresh_laliga_live()
        print(f'La Liga fixtures refreshed: {len(result["matches"])} at {result["updatedAt"]}')
    elif args.dataset == 'history':
        result = refresh_history('laliga')
        print(f'La Liga history: {len(result.transfers)} transfers, {len(result.managers)} manager changes')
    else:
        refresh_names(0, 'laliga')
        refresh_club_names('laliga')
        result = refresh_names(1000 if args.full else 60, 'laliga')
        print(f'La Liga names: {result.total - len(result.unresolved)}/{result.total}')
