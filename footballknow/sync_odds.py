import argparse
from football.odds import refresh_odds, refresh_official_checks

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('league', choices=['epl', 'laliga', 'ucl', 'seriea', 'bundesliga', 'sources'])
    args = parser.parse_args()
    snapshot = refresh_official_checks() if args.league == 'sources' else refresh_odds(args.league)
    print(f'{args.league}: {len(snapshot.get("matches", snapshot.get("sources", [])))} records checked')
