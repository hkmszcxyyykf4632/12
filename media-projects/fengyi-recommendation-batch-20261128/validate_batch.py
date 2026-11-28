from pathlib import Path
import json,subprocess,time,os
P=Path(__file__).resolve().parent
CLI='C:/Users/acer/.agents/skills/hyperframes/scripts/plugin-cli.mjs'
env=dict(os.environ,TEMP='D:/Codex-local-video-tools/fengyi-20261128/temp',TMP='D:/Codex-local-video-tools/fengyi-20261128/temp')
for ep in json.loads((P/'batch.json').read_text('utf8'))['episodes']:
    if ep['approvedSample']:continue
    d=P/ep['folder'];studio=d/'studio'
    while not (d/'asset-provenance.json').exists():time.sleep(2)
    if (d/'snapshot-review.txt').exists() and 'Phone sheet' in (d/'snapshot-review.txt').read_text('utf8'):
        print('PRESERVED_CHECK',ep['event'],flush=True);continue
    print('CHECKING',ep['event'],flush=True)
    out=subprocess.run(['node',CLI,'check','--json'],cwd=studio,env=env,capture_output=True,text=True,encoding='utf8')
    (d/'composition-check.json').write_text(out.stdout,encoding='utf8')
    if out.returncode:raise RuntimeError(out.stderr+out.stdout[-2000:])
    out=subprocess.run(['node',CLI,'snapshot','--review','--output',str(Path('D:/Codex-local-video-tools/fengyi-20261128/batch-review')/ep['event'])],cwd=studio,env=env,capture_output=True,text=True,encoding='utf8')
    (d/'snapshot-review.txt').write_text(out.stdout,encoding='utf8')
    if out.returncode:raise RuntimeError(out.stderr+out.stdout[-2000:])
    print('CHECKED',ep['event'],flush=True)
print('BATCH_CHECKS_COMPLETE',flush=True)
