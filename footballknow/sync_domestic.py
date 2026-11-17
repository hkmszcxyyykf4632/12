import argparse
from football.domestic import CONFIG, refresh_catalogue, refresh_live, refresh_history, refresh_localized_names

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('league', choices=CONFIG)
    parser.add_argument('kind', choices=['catalogue', 'live', 'history', 'names'])
    parser.add_argument('--full', action='store_true')
    args = parser.parse_args()
    if args.kind == 'live':
        result = refresh_live(args.league, args.full)
    elif args.kind == 'names':
        result = refresh_localized_names(args.league, args.full)
    else:
        result = (refresh_catalogue if args.kind == 'catalogue' else refresh_history)(args.league)
    print(f'{args.league} {args.kind}: published successfully')
