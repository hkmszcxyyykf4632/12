from pathlib import Path
import json,time,subprocess
import numpy as np
from faster_whisper import WhisperModel
P=Path(__file__).resolve().parent
model=WhisperModel('base',device='cpu',compute_type='int8',cpu_threads=4,download_root=str(P.parent/'fengyi-recommendation-original-characters/.speech-models'),local_files_only=True)
result={'method':'Automatic speech recognition, not a human listening judgement','entries':[]}
for entry in json.loads((P/'voice-generation.json').read_text('utf8'))['entries']:
    raw=subprocess.check_output(['ffmpeg','-v','error','-i',str(P/entry['file']),'-f','f32le','-ac','1','-ar','16000','pipe:1'])
    samples=np.frombuffer(raw,dtype=np.float32)
    segments,info=model.transcribe(samples,language='zh',beam_size=5,vad_filter=True)
    words=''.join(s.text for s in segments)
    result['entries'].append({'expected':entry['text'],'recognized':words,'file':entry['file']})
    (P/'speech-check.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf8')
    print(entry['text'],'=>',words,flush=True)
print('SPEECH_CHECK_COMPLETE',flush=True)
