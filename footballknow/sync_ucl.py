"""Run one independent Champions League refresh job."""
import argparse

from football.ucl import refresh_catalogue, refresh_live
from football.ucl_history import refresh_history, refresh_localized_names


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('dataset', choices=['catalogue', 'live', 'history', 'names'])
    parser.add_argument('--full', action='store_true')
    args = parser.parse_args()
    if args.dataset == 'catalogue':
        data = refresh_catalogue()
        print(f'UCL: {len(data["teams"])} clubs, {len(data["players"])} players, {len(data["matches"])} matches')
    elif args.dataset == 'live':
        data = refresh_live()
        print(f'UCL live: {len(data["matches"])} matches at {data["updatedAt"]}')
    elif args.dataset == 'history':
        data = refresh_history()
        print(f'UCL history: {len(data.transfers)} transfers, {len(data.managers)} manager changes')
    else:
        data = refresh_localized_names(args.full)
        print(f'UCL names: {len(data.names)}/{data.total}')
