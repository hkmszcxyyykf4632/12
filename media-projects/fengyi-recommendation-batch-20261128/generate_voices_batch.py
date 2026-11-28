from pathlib import Path
import hashlib,json,os,time,shutil
P=Path(__file__).resolve().parent
S=P.parent/'fengyi-local-sample-20261128'
os.environ['HF_HOME']='D:/Codex-local-video-tools/fengyi-20261128/model-cache'
os.environ['HF_HUB_DISABLE_TELEMETRY']='1'
import torch,soundfile as sf
from qwen_tts import Qwen3TTSModel
from huggingface_hub import snapshot_download
MODEL='Qwen/Qwen3-TTS-12Hz-0.6B-Base'
REV='5d83992436eae1d760afd27aff78a71d676296fc'
torch.set_num_threads(8);torch.set_num_interop_threads(2)
cache=P/'voice-cache';cache.mkdir(exist_ok=True)
ref=S/'audio/female-reference.wav'
model_dir=snapshot_download(MODEL,revision=REV,local_files_only=True)
model=Qwen3TTSModel.from_pretrained(model_dir,device_map='cpu',dtype=torch.float32,attn_implementation='sdpa')
prompt=model.create_voice_clone_prompt(ref_audio=str(ref),ref_text='今晚买博洛尼亚啊。博洛尼亚让乌迪内斯半球啊。',x_vector_only_mode=False)
receipt={'model':MODEL,'revision':REV,'paidCalls':0,'entries':[]}
for ep in json.loads((P/'batch.json').read_text('utf8'))['episodes']:
    if ep['approvedSample']: continue
    d=P/ep['folder'];(d/'audio').mkdir(exist_ok=True)
    lines=json.loads((d/'script.json').read_text('utf8'))['lines']
    for i,line in enumerate(lines):
        if line['source']=='original':continue
        dest=d/'audio'/f'line-{i+1:02d}.wav'
        if i==6:
            shutil.copy2(S/'audio/line-07.wav',dest);continue
        text=line['text'];key=hashlib.sha256(text.encode()).hexdigest()[:20];f=cache/(key+'.wav')
        if not f.exists():
            t=time.time();torch.manual_seed(28)
            print('GENERATING',ep['event'],i+1,text,flush=True)
            with torch.inference_mode():
                waves,sr=model.generate_voice_clone(text=text,language='Chinese',voice_clone_prompt=prompt,max_new_tokens=240)
            sf.write(f,waves[0],sr)
            receipt['entries'].append({'text':text,'file':f.relative_to(P).as_posix(),'seconds':len(waves[0])/sr,'generationSeconds':round(time.time()-t,2)})
            (P/'voice-generation.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf8')
        shutil.copy2(f,dest)
    print('VOICE_READY',ep['event'],flush=True)
receipt['complete']=True
(P/'voice-generation.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf8')
print('BATCH_VOICES_COMPLETE',flush=True)
