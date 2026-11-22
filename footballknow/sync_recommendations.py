"""Continuously publish upcoming selections without rewriting past picks."""
from football.recommendations import refresh
from football.sync_control import read_control

if __name__ == '__main__':
    print({'published': refresh() if read_control()['enabled'] else 0})
