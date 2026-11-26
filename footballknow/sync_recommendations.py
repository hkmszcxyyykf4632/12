"""Continuously publish upcoming selections without rewriting past picks."""
from football.recommendations import refresh, read_recommendations
from football.recommendation_video_queue import refresh_queue
from football.sync_control import read_control

if __name__ == '__main__':
    if read_control()['enabled']:
        published = refresh()
        queue = refresh_queue(read_recommendations()['records'])
        print({'published': published, 'videoQueued': len(queue['jobs'])})
    else:
        print({'paused': True})
