import json
from football.stock_automation import refresh

if __name__ == '__main__':
    print(json.dumps(refresh()))
