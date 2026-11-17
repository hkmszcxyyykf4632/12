from football.portal_news import sync_portal_news

if __name__ == '__main__':
    print(f'Chinese news: {sync_portal_news()} headlines')
