"""Refresh recent transfers and managerial changes once."""
from football.history import refresh_history

if __name__ == '__main__':
    snapshot = refresh_history()
    print(f'History: {len(snapshot.transfers)} transfers, {len(snapshot.managers)} managerial changes')
