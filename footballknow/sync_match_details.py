import argparse
from football.match_details import refresh_details

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('league', choices=['epl', 'laliga', 'ucl', 'seriea', 'bundesliga'])
    parser.add_argument('--limit', type=int, default=80)
    args = parser.parse_args()
    result = refresh_details(args.league, max(1, min(args.limit, 1200)))
    print(f'{args.league}: {result["available"]}/{result["targetMatches"]} lineups available')
