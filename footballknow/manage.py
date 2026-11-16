"""Generate the two administrator accounts without printing their passwords."""
import sys
from pathlib import Path

from football.auth import create_administrator_seed, initialize_database

if __name__ == '__main__':
    if sys.argv[1:] != ['init-admins']:
        raise SystemExit('Usage: python manage.py init-admins')
    destination = Path(__file__).resolve().parent.parent / 'FootballKnow_管理员账号_请保密.txt'
    created = create_administrator_seed(destination)
    initialize_database()
    print('Two administrator accounts created; credentials saved privately.' if created else 'Existing administrator accounts retained.')
