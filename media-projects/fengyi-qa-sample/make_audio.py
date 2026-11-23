import asyncio
import array
import json
import math
import pathlib
import subprocess
import edge_tts

ROOT = pathlib.Path(__file__).parent
OUT = ROOT / 'film' / 'assets' / 'audio'
OUT.mkdir(parents=True, exist_ok=True)
SEGMENTS = json.loads((ROOT / 'script.json').read_text(encoding='utf-8'))
VOICES = {'chief': 'zh-HK-WanLungNeural', 'angel': 'zh-HK-HiuMaanNeural'}

async def generate(i, row):
    path = OUT / f'{i:02d}.mp3'
    if not path.exists():
        await edge_tts.Communicate(row['text'], VOICES[row['speaker']], rate='+8%', pitch='+2Hz' if row['speaker'] == 'chief' else '+0Hz').save(str(path))
    probe = subprocess.check_output(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'json', str(path)])
    row['duration'] = float(json.loads(probe)['format']['duration'])
    pcm = subprocess.check_output(['ffmpeg', '-v', 'error', '-i', str(path), '-f', 's16le', '-ac', '1', '-ar', '12000', '-'])
    samples = array.array('h', pcm)
    rms = [math.sqrt(sum(v*v for v in samples[p:p+400])/max(1,len(samples[p:p+400])))/32768 for p in range(0,len(samples),400)]
    row['envelope'] = [round(v,4) for v in rms]
    row['src'] = f'assets/audio/{i:02d}.mp3'
    print(f'{i:02d} {row["speaker"]} {row["duration"]:.2f}s', flush=True)

async def main():
    # Small batches avoid concurrent voice-service spikes.
    for first in range(0, len(SEGMENTS), 3):
        await asyncio.gather(*(generate(i,SEGMENTS[i]) for i in range(first,min(first+3,len(SEGMENTS)))))
    time = 1.1
    for row in SEGMENTS:
        row['start'] = round(time,3)
        time += row['duration'] + (0.38 if row['speaker']=='chief' else 0.16)
    data = {'duration': round(time+2.0,3), 'segments':SEGMENTS, 'voices':VOICES}
    (ROOT/'timing.json').write_text(json.dumps(data, ensure_ascii=False, indent=2),encoding='utf-8')
    print('TOTAL',data['duration'],flush=True)

asyncio.run(main())
