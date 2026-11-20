import sys
from football.equity_markets import refresh_cn
from football.sync_control import read_control

if __name__ == '__main__':
    if not read_control()['enabled']:
        print('同步已暂停')
    elif len(sys.argv) == 1 or sys.argv[1] == 'cn':
        print(refresh_cn())
    elif sys.argv[1] == 'volume':
        from football.stock_volume import refresh_volume
        print(refresh_volume())
    elif sys.argv[1] == 'us':
        from football.us_reference import refresh_us
        print(refresh_us())
