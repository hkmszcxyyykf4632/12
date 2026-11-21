import argparse
import json
from football.data_backfill import refresh

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('kind', choices=['companies', 'horse-research'])
    parser.add_argument('--limit', type=int, default=24)
    args = parser.parse_args()
    print(json.dumps(refresh(args.kind, args.limit), ensure_ascii=False))
