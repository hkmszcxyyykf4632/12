from football.daily_scores import refresh_daily

if __name__ == '__main__':
    result = refresh_daily()
    print(f'Daily football: {len(result["matches"])} matches; pre-match records and outcome checks updated')
