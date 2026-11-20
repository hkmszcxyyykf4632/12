import argparse
from football.football_forecasts import refresh

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--bootstrap-day', help='One-off Hong Kong date for early initial forecasts')
    print(refresh(parser.parse_args().bootstrap_day))
