import argparse
from football.profiles import refresh_profiles
from football.leagues import LEAGUES

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('league', choices=LEAGUES)
    args = parser.parse_args()
    result = refresh_profiles(args.league)
    print(f"Club profiles: {len(result['teams'])}; pending: {len(result['failedTeams'])}")
