import argparse
from football.finance import refresh_assets, refresh_quotes, refresh_collection

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('kind', choices=['quotes', 'assets', 'companies', 'history', 'evaluation', 'catalogue'])
    args = parser.parse_args()
    if args.kind == 'catalogue':
        from football.hk_catalogue import refresh_catalogue
        result = refresh_catalogue()
    elif args.kind == 'evaluation':
        from football.stock_analysis import evaluate_all
        result = evaluate_all()
    elif args.kind in ['companies', 'history']:
        result = refresh_collection(args.kind)
    else:
        result = (refresh_quotes if args.kind == 'quotes' else refresh_assets)()
        if args.kind == 'assets':
            from football.global_markets import refresh_global_markets
            global_result = refresh_global_markets()
            if global_result['failedSymbols']:
                raise RuntimeError('Global quotes unavailable: ' + ', '.join(global_result['failedSymbols']))
    print('Finance ' + args.kind + ': refreshed ' + str(result.get('updatedAt', '')))
