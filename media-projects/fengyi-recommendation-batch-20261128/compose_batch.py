from pathlib import Path
import json,importlib.util,shutil,subprocess,os,time
P=Path(__file__).resolve().parent
S=P.parent/'fengyi-local-sample-20261128'
spec=importlib.util.spec_from_file_location('builder',P/'build_episode.py')
b=importlib.util.module_from_spec(spec);spec.loader.exec_module(b)
for ep in json.loads((P/'batch.json').read_text('utf8'))['episodes']:
    if ep['approvedSample']: continue
    d=P/ep['folder']
    while not all((d/'audio'/f'line-{i:02d}.wav').exists() for i in (2,4,6,7,8)):
        time.sleep(2)
    studio=d/'studio';(studio/'assets').mkdir(parents=True,exist_ok=True)
    for f in ['package.json','AGENTS.md']:
        shutil.copy2(S/'studio'/f,studio/f)
    b.P=d;b.STUDIO=studio;b.ASSETS=studio/'assets';b.main()
    print('COMPOSED',ep['event'],flush=True)
