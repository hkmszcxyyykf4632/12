import json,subprocess
from pathlib import Path
import numpy as np
from faster_whisper import WhisperModel
root=Path(__file__).resolve().parent
model=WhisperModel('base',device='cpu',compute_type='int8',cpu_threads=2,num_workers=1,download_root=str(root/'.speech-models'))
pcm=subprocess.check_output(['ffmpeg','-v','error','-i',str(root/'../../footballknow/public/media/videos/fengyi-recommendation-bologna-20261122-original-v3.mp4'),'-f','f32le','-ac','1','-ar','16000','-'])
segments,info=model.transcribe(np.frombuffer(pcm,dtype=np.float32),language='zh',beam_size=5,word_timestamps=True,vad_filter=False)
rows=[]
for s in segments:
 rows.append({'start':s.start,'end':s.end,'text':s.text,'words':[{'word':w.word,'start':w.start,'end':w.end,'probability':w.probability} for w in s.words or []]})
 print(s.start,s.end,s.text,flush=True)
(root/'speech-transcription.json').write_text(json.dumps({'language':info.language,'segments':rows,'note':'Automatic speech verification; not a human listening evaluation.'},ensure_ascii=False,indent=2),encoding='utf-8')
