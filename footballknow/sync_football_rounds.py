# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
# Run with the existing Football Know service environment: python sync_football_rounds.py
"""Bounded round-number refresh through the existing worker."""
from football.football_rounds import refresh
from football.sync_control import read_control

if __name__ == '__main__':
    print({'refreshed': refresh() if read_control()['enabled'] else 0})
