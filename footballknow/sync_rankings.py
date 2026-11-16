"""Refresh one named competition's table or leaders."""
import argparse

from football.rankings import refresh_leaders, refresh_standings


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('league', choices=['epl', 'laliga', 'ucl'])
    parser.add_argument('kind', choices=['standings', 'leaders'])
    args = parser.parse_args()
    snapshot = (refresh_standings if args.kind == 'standings' else refresh_leaders)(args.league)
    count = len(snapshot.get('entries', [])) if args.kind == 'standings' else {k: len(v) for k, v in snapshot['boards'].items()}
    print(f'{args.league} {args.kind}: {count}; {snapshot["updatedAt"]}')
