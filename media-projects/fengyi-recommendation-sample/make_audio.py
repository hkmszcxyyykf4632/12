import array
import asyncio
import json
import math
from pathlib import Path
import subprocess
import wave

import edge_tts

ROOT = Path(__file__).resolve().parent
AUDIO = ROOT / 'audio'
AUDIO.mkdir(parents=True, exist_ok=True)
SR = 48000
ROWS = [
    ('chief', '喂，今晚有什么好料啊？'),
    ('angel', '今晚买博洛尼亚啊。'),
    ('chief', '怎么让啊？'),
    ('angel', '博洛尼亚让乌迪内斯半球啊。'),
    ('chief', '买几比几啊？'),
    ('angel', '二比一啊。'),
]
VOICES = {'chief': 'zh-CN-YunxiNeural', 'angel': 'zh-CN-XiaoyiNeural'}


def write_wav(path, samples):
    with wave.open(str(path), 'wb') as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(SR)
        f.writeframes(samples.tobytes())


async def main():
    mixed = array.array('h', [0] * int(SR * .32))
    segments = []
    for i, (speaker, text) in enumerate(ROWS):
        path = AUDIO / f'{i + 1:02d}-{speaker}.mp3'
        boundary_path = path.with_suffix('.json')
        boundaries = []
        if not path.exists():
            talk = edge_tts.Communicate(text, VOICES[speaker], rate='+5%' if speaker == 'chief' else '+7%', pitch='-7Hz' if speaker == 'chief' else '+0Hz', boundary='WordBoundary')
            with path.open('wb') as f:
                async for part in talk.stream():
                    if part['type'] == 'audio':
                        f.write(part['data'])
                    elif part['type'] == 'WordBoundary':
                        boundaries.append(part)
            boundary_path.write_text(json.dumps(boundaries, ensure_ascii=False, indent=2), encoding='utf-8')
        elif boundary_path.exists():
            boundaries = json.loads(boundary_path.read_text(encoding='utf-8'))

        pcm = array.array('h', subprocess.check_output(['ffmpeg', '-v', 'error', '-i', str(path), '-ac', '1', '-ar', str(SR), '-f', 's16le', '-']))
        active = []
        for pos in range(0, len(pcm), 480):
            chunk = pcm[pos:pos + 480]
            if chunk and math.sqrt(sum(v * v for v in chunk) / len(chunk)) > 85:
                active.append(pos)
        if not active:
            raise RuntimeError(f'No audible speech in {path}')
        begin = max(0, active[0] - int(.065 * SR))
        end = min(len(pcm), active[-1] + 480 + int(.10 * SR))
        pcm = pcm[begin:end]
        peak = max(abs(v) for v in pcm)
        rms = math.sqrt(sum(v * v for v in pcm) / len(pcm))
        gain = min(1.65, 4300 / rms, 28000 / peak)
        pcm = array.array('h', [int(v * gain) for v in pcm])
        write_wav(AUDIO / f'{i + 1:02d}-trimmed.wav', pcm)
        start = len(mixed) / SR
        mixed.extend(pcm)
        envelope = []
        for pos in range(0, len(pcm), 480):
            chunk = pcm[pos:pos + 480]
            envelope.append(round(math.sqrt(sum(v * v for v in chunk) / len(chunk)) / 32768, 5))
        segments.append({
            'speaker': speaker, 'text': text, 'voice': VOICES[speaker],
            'start': round(start, 5), 'duration': round(len(pcm) / SR, 5),
            'envelopeHz': 100, 'envelope': envelope,
            'source': path.name, 'trimStart': begin / SR,
            'words': [{'text': b['text'], 'start': max(0, b['offset'] / 1e7 - begin / SR), 'duration': b['duration'] / 1e7} for b in boundaries],
        })
        if i < len(ROWS) - 1:
            pause = [.32, .27, .26, .28, .30][i]
            mixed.extend(array.array('h', [0] * int(SR * pause)))
        print(f'{i + 1}: {speaker} {len(pcm) / SR:.2f}s | {text}', flush=True)
    mixed.extend(array.array('h', [0] * int(SR * 1.4)))
    write_wav(AUDIO / 'dialogue.wav', mixed)
    subprocess.run(['ffmpeg', '-y', '-v', 'error', '-i', str(AUDIO / 'dialogue.wav'), '-af', 'loudnorm=I=-16:TP=-2:LRA=9', '-ar', '48000', '-ac', '2', str(AUDIO / 'dialogue-master.wav')], check=True)
    data = {'duration': len(mixed) / SR, 'segments': segments, 'voices': VOICES, 'language': 'Mandarin', 'method': 'Complete utterance neural speech, original user wording, measured conversational turn gaps', 'humanListeningVerified': False}
    (ROOT / 'timing.json').write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f'Total duration: {data["duration"]:.3f}s', flush=True)


if __name__ == '__main__':
    asyncio.run(main())
