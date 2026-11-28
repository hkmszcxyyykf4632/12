from pathlib import Path
import json,subprocess,time,os,shutil,hashlib
from datetime import datetime,timedelta,timezone
P=Path(__file__).resolve().parent
REPO=P.parents[1]
S=P.parent/'fengyi-local-sample-20261128'
CLI='C:/Users/acer/.agents/skills/hyperframes/scripts/plugin-cli.mjs'
TEMP=Path('D:/Codex-local-video-tools/fengyi-20261128/batch-renders');TEMP.mkdir(exist_ok=True)
PUBLIC=REPO/'footballknow/public/media/videos'
env=dict(os.environ,TEMP=str(TEMP),TMP=str(TEMP))
for ep in json.loads((P/'batch.json').read_text('utf8'))['episodes']:
    d=P/ep['folder'];job=json.loads((d/'recommendation-receipt.json').read_text('utf8'))
    day=datetime.fromisoformat(ep['kickoff'].replace('Z','+00:00')).astimezone(timezone(timedelta(hours=8))).strftime('%Y%m%d')
    name='fengyi-football-'+day+'-'+ep['event']+'-local-v1'
    output=PUBLIC/(name+'.mp4');poster=PUBLIC/(name+'.jpg')
    receipt_file=d/'media-check.json'
    if receipt_file.exists() and output.exists() and poster.exists():
        saved=json.loads(receipt_file.read_text('utf8'))
        if saved['sha256']==hashlib.sha256(output.read_bytes()).hexdigest():
            print('PRESERVED_RENDER',ep['event'],flush=True)
            continue
    if ep['approvedSample']:
        shutil.copy2(S/'fengyi-local-sample-web.mp4',output)
    else:
        while not (d/'visual-review.json').exists():time.sleep(2)
        assert json.loads((d/'composition-check.json').read_text('utf8'))['ok']
        print('RENDERING',ep['event'],flush=True)
        master=TEMP/(ep['event']+'-master.mp4')
        log=(d/'render.log').open('w',encoding='utf8')
        if not master.exists():
            subprocess.run(['node',CLI,'render','--fps','24','--workers','2','--crf','20','--strict','--no-best-effort','--frames-cache-dir',str(TEMP/(ep['event']+'-frames')),'-o',str(master)],cwd=d/'studio',env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
        subprocess.run(['ffmpeg','-y','-v','error','-i',str(master),'-c:v','libx264','-preset','fast','-crf','24','-maxrate','3M','-bufsize','6M','-pix_fmt','yuv420p','-threads','4','-c:a','aac','-b:a','128k','-movflags','+faststart',str(output)],check=True)
    subprocess.run(['ffmpeg','-y','-v','error','-ss','0.5','-i',str(output),'-frames:v','1','-q:v','3',str(poster)],check=True)
    info=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_streams','-show_format','-of','json',str(output)],text=True,encoding='utf8'))
    video=next(s for s in info['streams'] if s['codec_type']=='video');audio=next(s for s in info['streams'] if s['codec_type']=='audio')
    raw=output.read_bytes()
    assert video['codec_name']=='h264' and audio['codec_name']=='aac'
    assert video['width']==1344 and video['height']==768 and video['r_frame_rate']=='24/1'
    assert raw.find(b'moov')<raw.find(b'mdat') and raw.find(b'moov')>=0
    record={'file':output.relative_to(REPO).as_posix(),'poster':poster.relative_to(REPO).as_posix(),'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest(),'duration':float(info['format']['duration']),'width':1344,'height':768,'fps':24,'video':'h264','audio':'aac','fastStart':True}
    (d/'media-check.json').write_text(json.dumps(record,indent=2),encoding='utf8')
    print('RENDERED',ep['event'],record['duration'],record['bytes'],flush=True)
print('BATCH_RENDER_COMPLETE',flush=True)
