"""Build an editable local dialogue trial from approved footage and new speech."""
from pathlib import Path
import hashlib
import json
import subprocess
import urllib.request

P = Path(__file__).resolve().parent
REPO = P.parents[1]
SOURCE = REPO / 'footballknow/public/media/videos/fengyi-recommendation-bologna-20261122-original-v3.mp4'
STUDIO = P / 'studio'
ASSETS = STUDIO / 'assets'


def run(args):
    subprocess.run(args, check=True)


def duration(path):
    return float(subprocess.check_output(['ffprobe', '-v', 'error', '-show_entries',
                                        'format=duration', '-of', 'csv=p=0', str(path)], text=True).strip())


def main():
    ASSETS.mkdir(exist_ok=True)
    (ASSETS / 'gsap.min.js').write_bytes(urllib.request.urlopen(
        'https://cdn.jsdelivr.net/npm/gsap@3.15.0/dist/gsap.min.js', timeout=45).read())
    vendor = ASSETS / 'gsap.min.js'
    vendor.write_text(chr(10).join(line.rstrip() for line in vendor.read_text(encoding='utf-8').splitlines()).rstrip() + chr(10), encoding='utf-8')
    lines = json.loads((P / 'script.json').read_text(encoding='utf-8'))['lines']
    footage_windows = [(0, 2.4), (2.4, 4.4), (4.4, 5.62), (5.65, 8.45),
                       (8.45, 10.05), (5.65, 8.45), (4.4, 5.62), (5.65, 8.45)]
    start = 0
    timeline, tags = [], []
    concat_inputs = []
    for i, (line, (vstart, vend)) in enumerate(zip(lines, footage_windows)):
        raw_audio = P / 'audio' / f'line-{i + 1:02d}.wav'
        if line['source'] == 'original':
            run(['ffmpeg', '-y', '-v', 'error', '-ss', str(line['start']), '-to', str(line['end']),
                 '-i', str(SOURCE), '-vn', '-ac', '1', '-ar', '24000', str(raw_audio)])
        if i == 7:
            trimmed = P / 'audio' / 'line-08-trimmed.wav'
            run(['ffmpeg', '-y', '-v', 'error', '-i', str(raw_audio), '-t', '3.22', str(trimmed)])
            raw_audio = trimmed
        speech_duration = duration(raw_audio)
        # Round all scene boundaries to complete 24 fps frames.
        frames = round((speech_duration + (0.12 if i < 7 else 0.4)) * 24)
        length = frames / 24
        clip = ASSETS / f'turn-{i + 1:02d}.mp4'
        audio = ASSETS / f'dialogue-{i + 1:02d}.wav'
        # Retiming reuses the original movement; it is not phoneme-level lip sync.
        ratio = length / (vend - vstart)
        run(['ffmpeg', '-y', '-v', 'error', '-ss', str(vstart), '-to', str(vend), '-i', str(SOURCE),
             '-an', '-vf', f'setpts={ratio}*(PTS-STARTPTS),fps=24,tpad=stop_mode=clone:stop_duration=0.2',
             '-frames:v', str(frames), '-c:v', 'libx264', '-preset', 'fast', '-crf', '19',
             '-pix_fmt', 'yuv420p', '-threads', '4', '-movflags', '+faststart', str(clip)])
        run(['ffmpeg', '-y', '-v', 'error', '-i', str(raw_audio), '-af',
             'loudnorm=I=-18:TP=-1.5:LRA=8,apad', '-t', str(length), '-ar', '48000', '-ac', '2', str(audio)])
        audio_slot = min(duration(audio), length - 0.00001)
        tags.extend([
            f'      <video id="turn-{i+1}" class="clip footage" src="assets/{clip.name}" muted playsinline data-start="{start:.6f}" data-duration="{length:.6f}" data-track-index="0"></video>',
            f'      <audio id="dialogue-{i+1}" class="clip" src="assets/{audio.name}" data-start="{start:.6f}" data-duration="{audio_slot:.6f}" data-track-index="1" data-volume="1"></audio>',
        ])
        timeline.append(dict(line=i + 1, role=line['role'], text=line['text'], start=round(start, 6),
                             duration=round(length, 6), audioSource=line['source'],
                             originalFootageWindow=[vstart, vend], videoPlaybackSpeed=round(1 / ratio, 4)))
        concat_inputs.append(audio)
        start += length
    html = '''<!doctype html>
<html lang="zh-CN">
  <head><meta charset="UTF-8"><meta name="viewport" content="width=1344, height=768">
    <title>峰弈推荐 · 本地声音试样</title>
    <script src="assets/gsap.min.js"></script>
    <style>html,body{margin:0;width:1344px;height:768px;overflow:hidden;background:#302a20}#root{position:relative;width:100%;height:100%;overflow:hidden}.footage{position:absolute;inset:0;width:100%;height:100%;object-fit:contain}</style>
  </head><body>
    <div id="root" data-composition-id="main" data-start="0" data-duration="DURATION" data-width="1344" data-height="768">
CLIPS
    </div>
    <script>window.__timelines["main"]=gsap.timeline({paused:true});</script>
  </body>
</html>
'''.replace('DURATION', f'{start:.6f}').replace('CLIPS', '\n'.join(tags))
    (STUDIO / 'index.html').write_text(html, encoding='utf-8')
    (P / 'timeline.json').write_text(json.dumps({'fps': 24, 'duration': start, 'turns': timeline}, ensure_ascii=False, indent=2), encoding='utf-8')
    # Export a single speech track for transcription and waveform checks.
    args = ['ffmpeg', '-y', '-v', 'error']
    for audio in concat_inputs:
        args += ['-i', str(audio)]
    filters = ''.join(f'[{i}:a]' for i in range(8)) + 'concat=n=8:v=0:a=1[out]'
    run(args + ['-filter_complex', filters, '-map', '[out]', str(P / 'dialogue-mix.wav')])
    manifest = {'originalVideo': str(SOURCE.relative_to(REPO)).replace(chr(92), '/'),
                'originalSha256': hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
                'voiceSource': 'User-approved synthetic character dialogue, locally reference-conditioned with Qwen3-TTS.',
                'paidCalls': 0, 'published': False, 'preciseLipSync': False,
                'purpose': 'Private local technical trial; not a newly issued recommendation.',
                'clips': [{'path': f'studio/assets/{f.name}', 'sha256': hashlib.sha256(f.read_bytes()).hexdigest()}
                          for f in ASSETS.iterdir() if f.suffix in {'.mp4', '.wav'}]}
    (P / 'asset-provenance.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f'BUILT {len(lines)} turns, {start:.3f}s', flush=True)


if __name__ == '__main__':
    main()
