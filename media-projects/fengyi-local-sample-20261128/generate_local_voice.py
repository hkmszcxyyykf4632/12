"""Evaluate local speech using the user's approved, synthetic character voices.

Models and the isolated Python environment live outside the repository.
No paid generation endpoint, site publishing, or account credentials are used.
"""
from pathlib import Path
import json
import os
import subprocess
import time
import urllib.request

PROJECT = Path(__file__).resolve().parent
REPO = PROJECT.parents[1]
CACHE = Path(os.environ.get('FENGYI_MODEL_CACHE', str(REPO.parent / 'local-voice-tools' / 'model-cache')))
os.environ['HF_HOME'] = str(CACHE)
os.environ['HF_HUB_DISABLE_TELEMETRY'] = '1'
os.environ['HF_HUB_DISABLE_SYMLINKS_WARNING'] = '1'
SOURCE = REPO / 'footballknow/public/media/videos/fengyi-recommendation-bologna-20261122-original-v3.mp4'
MODEL = 'Qwen/Qwen3-TTS-12Hz-0.6B-Base'


def extract_reference(name, windows):
    audio_dir = PROJECT / 'audio'
    audio_dir.mkdir(exist_ok=True)
    chains = []
    for i, (start, end) in enumerate(windows):
        chains.append(f'[0:a]atrim=start={start}:end={end},asetpts=PTS-STARTPTS[a{i}]')
    chains.append(''.join(f'[a{i}]' for i in range(len(windows))) +
                  f'concat=n={len(windows)}:v=0:a=1[out]')
    output = audio_dir / f'{name}-reference.wav'
    subprocess.run(['ffmpeg', '-y', '-v', 'error', '-i', str(SOURCE),
                    '-filter_complex', ';'.join(chains), '-map', '[out]',
                    '-ac', '1', '-ar', '24000', str(output)], check=True)
    return output


def main():
    started = time.time()
    previous = PROJECT / 'voice-generation.json'
    script_lines = json.loads((PROJECT / 'script.json').read_text(encoding='utf-8'))['lines']
    if previous.exists():
        saved = json.loads(previous.read_text(encoding='utf-8'))
        expected = [PROJECT / 'audio' / f'line-{i + 1:02d}.wav' for i, line in enumerate(script_lines) if line['source'] == 'local']
        if saved.get('completed') and all(path.exists() for path in expected):
            print('Completed local dialogue already exists; preserving its provenance.', flush=True)
            return
    print('Preparing approved synthetic voice references', flush=True)
    references = {
        'female': (extract_reference('female', [(2.4, 4.4), (5.65, 8.45)]),
                   '今晚买博洛尼亚啊。博洛尼亚让乌迪内斯半球啊。'),
        'male': (extract_reference('male', [(0, 2.4), (4.4, 5.62), (8.45, 10.05)]),
                 '喂，今晚有什么好料啊？怎么让啊？买几比几啊？'),
    }
    print('Loading CPU speech runtime', flush=True)
    import torch
    import soundfile as sf
    from qwen_tts import Qwen3TTSModel
    from huggingface_hub import snapshot_download

    torch.set_num_threads(8)
    torch.set_num_interop_threads(2)
    torch.manual_seed(28)
    with urllib.request.urlopen(f'https://huggingface.co/api/models/{MODEL}', timeout=45) as response:
        revision = json.load(response)['sha']
    print(f'Downloading {MODEL} at {revision}', flush=True)
    model_dir = snapshot_download(MODEL, revision=revision,
                                  ignore_patterns=['*.bin', '*.pt', '*.pth', '*.msgpack'])
    print('Loading model on CPU', flush=True)
    model = Qwen3TTSModel.from_pretrained(model_dir, device_map='cpu',
                                        dtype=torch.float32, attn_implementation='sdpa')
    prompts = {}
    lines = json.loads((PROJECT / 'script.json').read_text(encoding='utf-8'))['lines']
    receipt = {'model': MODEL, 'revision': revision, 'device': 'cpu',
               'torchVersion': torch.__version__, 'paidGenerationCalls': 0,
               'sourceIsSyntheticCharacterSpeech': True, 'lines': []}
    # First test the changed female answer before making the remaining lines.
    for i, line in enumerate(lines):
        if line['source'] != 'local':
            continue
        output = PROJECT / 'audio' / f'line-{i + 1:02d}.wav'
        if output.exists():
            print(f'Skipping completed {output.name}', flush=True)
            continue
        role = line['role']
        if role not in prompts:
            ref, text = references[role]
            print(f'Preparing {role} voice prompt', flush=True)
            prompts[role] = model.create_voice_clone_prompt(ref_audio=str(ref),
                                                           ref_text=text,
                                                           x_vector_only_mode=False)
        print(f'Generating line {i + 1}: {line["text"]}', flush=True)
        line_start = time.time()
        with torch.inference_mode():
            wavs, sr = model.generate_voice_clone(text=line['text'], language='Chinese',
                                                 voice_clone_prompt=prompts[role],
                                                 max_new_tokens=180)
        sf.write(output, wavs[0], sr)
        receipt['lines'].append({'line': i + 1, 'text': line['text'],
                                 'durationSeconds': len(wavs[0]) / sr,
                                 'generationSeconds': round(time.time() - line_start, 2),
                                 'file': f'audio/{output.name}'})
        (PROJECT / 'voice-generation.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2), encoding='utf-8')
        print(f'Finished {output.name} in {time.time() - line_start:.1f}s', flush=True)
    receipt['totalSeconds'] = round(time.time() - started, 2)
    receipt['completed'] = True
    (PROJECT / 'voice-generation.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2), encoding='utf-8')
    print('LOCAL_VOICES_COMPLETE', flush=True)


if __name__ == '__main__':
    main()
