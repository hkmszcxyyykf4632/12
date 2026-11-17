import argparse
from football.leagues import LEAGUES
from football.news import refresh_news

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('league', choices=LEAGUES)
    args = parser.parse_args()
    result = refresh_news(args.league)
    print(f'{args.league} news: {len(result["articles"])} headlines')
