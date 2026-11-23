import bpy
import json
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
scene = bpy.context.scene
scene.eevee.taa_render_samples = 16
scene.render.filepath = str(ROOT / 'frames' / 'frame_')
scene.render.image_settings.compression = 20
started = time.time()


def done_frame(scene):
    (ROOT / 'render-progress.json').write_text(json.dumps({
        'frame': scene.frame_current, 'total': scene.frame_end,
        'elapsed': round(time.time() - started, 1), 'completed': False,
    }), encoding='utf-8')


bpy.app.handlers.render_post.append(done_frame)
bpy.ops.render.render(animation=True)
(ROOT / 'render-progress.json').write_text(json.dumps({
    'frame': scene.frame_end, 'total': scene.frame_end,
    'elapsed': round(time.time() - started, 1), 'completed': True,
}), encoding='utf-8')
