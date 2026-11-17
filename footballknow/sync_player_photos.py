import sys
from football.player_photos import sync_player_photos
from football.player_values import sync_player_values

if __name__ == '__main__':
    print('Player portraits:', sync_player_photos(sys.argv[1], int(sys.argv[2]) if len(sys.argv) > 2 else 60))
    print('Player valuations:', sync_player_values(sys.argv[1]))
