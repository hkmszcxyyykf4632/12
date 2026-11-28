from pathlib import Path
import json, shutil
P=Path(__file__).resolve().parent
S=P.parent/'fengyi-local-sample-20261128'
def write(path,value):
    path.write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf8')
reasons={
'401882796':'贝蒂斯从让一球半，退到半球啊。',
'401884719':'受让半球，赔率变化信号比较弱啊。',
'401879226':'受让半球，去水后的权重升了啊。',
'401882790':'让半球，去水后的权重升了啊。',
'401884726':'受让半球，法兰克福赔率降了啊。',
'401874977':'受让一球半，热那亚赔率降了啊。',
'401875031':'受让半球，乌迪内斯赔率降了啊。',
'401874992':'让半球，那不勒斯赔率略降了啊。',
'401879230':'受让半球，去水后的权重升了啊。',
'401884727':'受让半球，赔率变化信号比较弱啊。',
'401882788':'让半球，皇家社会赔率降了啊。',
'401879221':'让半球，赔率变化信号比较弱啊。'}
base=json.loads((S/'script.json').read_text('utf8'))
jobs=json.loads((P/'live-video-queue.json').read_text('utf8'))['jobs']
manifest=[]
for job in jobs:
    eid=job['event'];d=P/'episodes'/eid;d.mkdir(parents=True,exist_ok=True)
    write(d/'recommendation-receipt.json',job)
    if eid=='401879229':
        script=base.copy();script['purpose']='Approved local sample, now authorized for publication against the original frozen recommendation.'
    else:
        lines=[dict(x) for x in base['lines']]
        for i in (1,3,5): lines[i]['text']=job['dialogue'][i]
        lines[3]['text']=lines[3]['text'].replace('04','零四')
        lines[1]['text']=lines[1]['text'].replace('04','零四')
        lines[5]['text']='主队在前，'+lines[5]['text']
        lines[7]['text']=reasons[eid]
        script={'purpose':'Video of the existing frozen recommendation; not a new forecast.','lines':lines}
    script['sourceRecommendation']='recommendation-receipt.json'
    write(d/'script.json',script)
    manifest.append({'event':eid,'folder':'episodes/'+eid,'kickoff':job['kickoff'],'approvedSample':eid=='401879229','title':job['title']})
write(P/'batch.json',{'episodes':manifest,'paidGenerationCalls':0,'template':'../fengyi-local-sample-20261128','scoreOrder':'Home first, except approved Liverpool speech describes Liverpool wins; explicitly labelled in publication.'})
print('Prepared',len(manifest),'episodes')
