import json
import math
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parent
DATA = json.loads((ROOT / 'timing.json').read_text(encoding='utf-8'))
END = math.ceil(DATA['duration'] * 24) / 24


def stamp(s):
    cs = round(s * 100)
    return f'{cs//360000}:{cs//6000%60:02d}:{cs//100%60:02d}.{cs%100:02d}'


header = '''[Script Info]
ScriptType: v4.00+
PlayResX: 1280
PlayResY: 720
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Main,Microsoft YaHei,36,&H00FFFFFF,&H00FFFFFF,&H00301E10,&H00000000,-1,0,0,0,100,100,0,0,1,1,0,5,35,35,35,1
Style: Small,Microsoft YaHei,22,&H00FFFFFF,&H00FFFFFF,&H00301E10,&H00000000,0,0,0,0,100,100,0,0,1,0,0,5,35,35,35,1
Style: Shape,Arial,20,&H00301E10,&H00301E10,&H00301E10,&H00000000,0,0,0,0,100,100,0,0,1,0,0,7,0,0,0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
'''
events = []


def event(layer, start, end, style, text):
    events.append(f'Dialogue: {layer},{stamp(start)},{stamp(end)},{style},,0,0,0,,{text}')


def panel(x, y, w, h, r, start, end):
    path = f'm {r} 0 l {w-r} 0 b {w} 0 {w} {r} {w} {r} l {w} {h-r} b {w} {h} {w-r} {h} {w-r} {h} l {r} {h} b 0 {h} 0 {h-r} 0 {h-r} l 0 {r} b 0 0 {r} 0 {r} 0'
    event(0, start, end, 'Shape', f'{{\\an7\\pos({x},{y})\\p1\\1c&H251A10&\\1a&H20&}}{path}{{\\p0}}')


panel(28, 23, 164, 45, 13, 0, END)
event(2, 0, END, 'Main', r'{\pos(110,45)\fs26\bord0\1c&HD1E7F8&}峰弈推荐')
panel(917, 23, 335, 45, 13, 0, END)
event(2, 0, END, 'Small', r'{\pos(1085,46)\fs20}2026.11.22 · 历史推荐示范')
event(2, 0, END, 'Small', r'{\pos(640,46)\fs21\bord1\1c&HFFFFFF&}博洛尼亚 vs 乌迪内斯')

for i, s in enumerate(DATA['segments']):
    stop = DATA['segments'][i+1]['start'] if i+1<len(DATA['segments']) else END
    panel(148, 610, 984, 78, 18, s['start'], stop)
    who = '大首领' if s['speaker']=='chief' else '大天使'
    color = '&H9BC8F1&' if s['speaker']=='chief' else '&HDAE8C8&'
    text = f'{{\\pos(640,649)\\fs21\\1c{color}}}{who}  {{\\fs36\\1c&HFFFFFF&}}{s["text"]}'
    event(2, s['start'], stop, 'Main', text)
last = DATA['segments'][-1]
event(2, last['start'] + last['duration'], END, 'Small', r'{\pos(640,588)\fs23\bord2}博洛尼亚让半球 · 预测比分 2:1')
(ROOT / 'captions.ass').write_text(header + '\n'.join(events) + '\n', encoding='utf-8-sig')

if __name__ == '__main__':
    output = ROOT / '峰弈推荐-三问三答-历史样板.mp4'
    expected = math.ceil(DATA['duration']*24)
    frames = list((ROOT/'frames').glob('frame_*.png'))
    if len(frames) != expected:
        print(f'Captions ready; rendered frames {len(frames)}/{expected}.')
        raise SystemExit(0)
    subprocess.run([
        'ffmpeg','-y','-hide_banner','-loglevel','warning',
        '-framerate','24','-i','frames/frame_%04d.png','-i','audio/dialogue-master.wav',
        '-vf','hqdn3d=1.2:1.2:2:2,ass=captions.ass',
        '-c:v','libx264','-preset','slow','-crf','18','-pix_fmt','yuv420p',
        '-c:a','aac','-b:a','192k','-ar','48000','-movflags','+faststart',
        '-t',str(END),str(output),
    ], cwd=ROOT, check=True)
    probe = json.loads(subprocess.check_output(['ffprobe','-v','error','-show_format','-show_streams','-of','json',str(output)]))
    (ROOT/'final-probe.json').write_text(json.dumps(probe,ensure_ascii=False,indent=2),encoding='utf-8')
    print(output)
