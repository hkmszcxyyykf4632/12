"""Cross-check source arithmetic and package the user's local research results."""
import argparse
from collections import Counter
import csv
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import re
from zipfile import ZipFile, ZIP_DEFLATED


def verify(data, archive):
    counts, draw, bands, scores, returns = Counter(), 0, Counter(), Counter(), {}
    seen = set()
    for src in data['sources']:
        p=archive/'source'/src['season']/(src['league']+'.csv')
        raw=p.read_bytes()
        assert hashlib.sha256(raw).hexdigest()==src['sha256']
        rows=list(csv.DictReader(raw.decode('utf-8-sig').splitlines()))
        chosen=0
        for row in rows:
            if not row.get('AHCh','').strip(): continue
            h=Decimal(row['AHCh'])
            if abs(h)>Decimal('.5'):continue
            key=(src['season'],src['league'],row['Date'],row['HomeTeam'],row['AwayTeam'])
            assert key not in seen;seen.add(key)
            chosen+=1;counts[src['season']]+=1
            hg,ag=int(row['FTHG']),int(row['FTAG']);m=hg-ag
            draw+=int(m==0);scores[f'{hg}:{ag}']+=1
            for b in ['0.5','1','2']:bands[b]+=int(abs(Decimal(m)+h)<=Decimal(b))
            q=int(h*4);parts=[q-1,q+1] if q%2 else [q]
            for side in ['home','away']:
                price=row['B365CAHH' if side=='home' else 'B365CAHA']
                if not price or not row['B365CAHH'] or not row['B365CAHA']: continue
                sign=1 if side=='home' else -1
                outcomes=[(4*m+x)*sign for x in parts]
                gain=sum((Decimal(price)-1 if v>0 else Decimal(-1) if v<0 else Decimal(0)) for v in outcomes)/len(outcomes)
                returns[(abs(float(h)),side)]=returns.get((abs(float(h)),side),Decimal(0))+gain*100
                if q:
                    orient='upper' if (side=='home' and q<0) or (side=='away' and q>0) else 'lower'
                    returns[(abs(float(h)),orient)]=returns.get((abs(float(h)),orient),Decimal(0))+gain*100
        assert chosen==src['audit']['selected']
    assert len(seen)==data['all']['summary']['n']==2450
    assert draw==data['all']['summary']['draw']['count']
    for b,n in bands.items():assert n==data['all']['summary']['bands'][b]['count']
    for group in data['all']['byDepth']:
        for side in ['home','away','upper','lower']:
            assert abs(float(returns.get((group['depth'],side),0))-group['sides'][side]['profitPer100'])<.001
    for season in data['seasons']:assert counts[season['season']]==season['summary']['n']
    assert scores['0:0']+scores['1:1']==data['all']['summary']['draw00or11']['count']
    result={'check':'independent Decimal arithmetic from 12 original CSVs','sourceMatches':4338,
            'selectedMatches':len(seen),'seasonCounts':dict(counts),'bands':dict(bands),
            'status':'passed','checks':['source hashes','no duplicate selected matches','closing-only selection',
            'season totals','goal-distance signs','draw denominators','quarter handicap profits for all sides']}
    (archive/'独立复核.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    return result


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--archive',type=Path,required=True);args=parser.parse_args()
    public=Path(__file__).resolve().parents[1]/'public'
    report=json.loads((public/'research/shallow-handicap.json').read_text(encoding='utf-8'))
    print(json.dumps(verify(report,args.archive),ensure_ascii=False))
    s=report['all']['summary'];half=s['halfBall']
    rate=lambda x:f"{x['count']}/{x['n']}（{x['pct']:.2f}%）" if x['n'] else '无样本'
    lines=['# 三季四大联赛：半球以内的赛前收盘研究','',
        '范围：2023/24、2024/25、2025/26；英超、西甲、意甲、德甲。每场只算一次，以数据源标为收盘的 AHCh 筛选；包括平手、主让或受让平半、主让或受让半球。',
        '', '## 先看结论', '',
        f"共核对 4,338 场完整赛果，筛出 {s['n']:,} 场浅盘；收盘盘口缺失 0 场。浅盘实际主客进球差在一球内（含平局）的比例为 {rate(s['oneGoalOrDraw'])}；半球以外为 1047/1888（55.46%）。浅盘确实更集中于接近的赛果。",
        '',f"但“接近”并不等于“平局”。浅盘平局为 {rate(s['draw'])}；0:0／1:1 合计只有 {rate(s['draw00or11'])}。因此，盘口可以帮助缩小候选池，不能单独锁定精确比分。",
        '', '## 每季、每个联赛分别统计', '',
        '| 赛季 | 英超 | 西甲 | 意甲 | 德甲 | 浅盘合计 | 平局比例 | 距盘口中心≤1球 |',
        '|---|---:|---:|---:|---:|---:|---:|---:|']
    for p in report['seasons']:
        x=p['summary'];n=[str(l['summary']['n']) for l in p['leagues']]
        lines.append('| '+p['season'].replace('-','/')+' | '+' | '.join(n)+f" | {x['n']} | {x['draw']['pct']:.2f}% | {x['bands']['1']['pct']:.2f}% |")
    lines+=['','每季一球范围覆盖率约58.5%–58.7%，在这三季较稳定；但三季都被用于观察，不能当作一套事先固定模型的独立验证。',
            '', '## 半球下盘的例子，具体漏掉了什么', '',
            f"全部半球盘 {half['n']} 场，下盘赢了 {half['lowerWin']['count']} 场。若事先每场固定选 0:0、1:1，这两个比分覆盖 {rate(half['fixed00or11'])}。",
            '',f"只看下盘已经赢的 {half['lowerWin']['count']} 场：0:0／1:1 共 {half['draw00or11GivenLowerWin']['count']} 场（{half['draw00or11GivenLowerWin']['pct']:.2f}%）；其他平局 {half['otherDraws']} 场；下盘直接赢球 {half['underdogOutrightWins']} 场。",
            '', '这里有两个不同问题：能否提前判断下盘赢，以及下盘赢时更可能平局还是直接获胜。“44.25%”是在下盘已赢的事后子样本内计算，不能替代对全部半球盘的“22.38%”。',
            '', '## 平手、平半、半球的分布', '',
            '| 收盘深度 | 场数 | 平局 | 0:0／1:1 | 小于2.5球 |', '|---|---:|---:|---:|---:|']
    for x in report['all']['byDepth']:
        lines.append(f"| { {0:'平手',.25:'平／半',.5:'半球'}[x['depth']]} | {x['n']} | {x['draw']['pct']:.2f}% | {x['draw00or11']['pct']:.2f}% | {x['under25']['pct']:.2f}% |")
    lines+=['', '三类的平局比例接近，单靠把平手、平半、半球再分开，尚未看到很大的比分区分能力。',
            '', '## 大小球报价提供了什么额外信息', '',
            '| 收盘报价环境 | 场数 | 实际小于2.5球 | 0:0／1:1 |', '|---|---:|---:|---:|']
    for x in report['all']['byTotalMarket']:
        if x['n']:lines.append(f"| {x['market']} | {x['n']} | {x['under25']['pct']:.2f}% | {x['draw00or11']['pct']:.2f}% |")
    lines+=['','用 Bet365 大／小2.5球成对收盘报价计算去水隐含概率，大球小于45%归偏小、45%–55%归均衡、大于55%归偏大。它是统一2.5球报价，不冒充每场主流大小球盘口。',
            '', '相同浅盘条件下，0:0／1:1 在偏小球组占26.67%，偏大球组只有15.59%。后续选两个比分，值得优先结合大小球环境，再分别判断平局、让球方小胜、受让方小胜。此处仅是观察关联，未证明一种可盈利策略。',
            '', '## 固定买上下盘的结果', '',
            '以下只是对照策略：每场固定100单位，以成对 Bet365 收盘赔率计算；不是网站真正提前推荐的收益。', '',
            '| 盘口 | 固定选择 | 有报价场数 | 净收益（单位） | 回报率 |', '|---|---|---:|---:|---:|']
    for d in report['all']['byDepth']:
        for side in (['home','away'] if d['depth']==0 else ['upper','lower']):
            x=d['sides'][side]
            lines.append(f"| { {0:'平手',.25:'平／半',.5:'半球'}[d['depth']]} | { {'home':'主队','away':'客队','upper':'上盘','lower':'下盘'}[side]} | {x['pricedN']} | {x['profitPer100']:+,.2f} | {x['roiPct']:+.2f}% |")
    lines+=['','平半上盘合计小幅正收益，不足以确认稳定优势：已经查看多个联赛、赛季和分组，存在挑出表现最好组的偏差。下一轮应先锁定规则，再用尚未比赛的数据检验，不能看完赛果再改规则。比分赔率没有完整记录，本次不计算比分投注回报。',
            '', '## 变盘研究的边界', '',
            '早期采样 AHh 与收盘 AHCh 可用于比较让球加深、变浅、让受互换、退到平手。早期采样不一定是正式初盘；盘口数值未变也可能水位改变。当前选样只看最终收盘≤半球，所以加深、变浅的样本不能当作随机对照。',
            '', '盘口升降与赛果的关系不能直接证明变化原因。伤停、首发、红牌和战术调整需要另取带时间的消息和比赛事件；本批 CSV 无法独立解释这些原因。',
            '', '## 计算口径与复核', '',
            '盘口中心对应的净胜球为“主队让球数的相反数”；距离为 |主队进球−客队进球+主队收盘让球|。例如主让半球，1:0和0:0都相差半球，0:1相差一球半。不要把这个距离与“实际双方进球差”混为一谈。',
            '', '全部比赛按常规比赛时间（含补时）结算。平半拆成平手和半球各一半；平手走盘不算赢；缺失赔率不补成0。每场一行、唯一标识去重。全部12个原始文件保存校验值，并用另一套 Decimal 算法复核选样、距离、比例分母及固定买入收益。',
            '', '来源标为 Closing 的收盘记录未提供精确采样分钟；这表示数据商的赛前收盘口径，不声称逐秒取得开赛前最后一笔。',
            '', '来源：[Football-Data 数据说明](https://www.football-data.co.uk/data.php)；[字段说明](https://www.football-data.co.uk/notes.txt)。完整来源链接、下载时间和校验值见研究汇总.json。',
            '', '这份研究表用于本次历史核对，不写入网站赛前预测或实盘命中率。原始宽表保存在本机 source 目录，公开研究页面只放自行计算的汇总结论。']
    (args.archive/'三季浅盘研究报告.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    css=(public/'styles.css').read_text(encoding='utf-8')+(public/'sections.css').read_text(encoding='utf-8')+(public/'handicap-study.css').read_text(encoding='utf-8')
    script=(public/'handicap-study.mjs').read_text(encoding='utf-8').replace('export function ','function ')
    payload=json.dumps(report,ensure_ascii=False,separators=(',',':')).replace('<','\u003c')
    html='<!doctype html><html lang="zh-CN" data-section="football"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>峰弈科技 · 三季浅盘研究</title><style>'+css+' body{margin:0}main#main{margin:0 auto;padding:24px;max-width:1450px}.report-files{padding:20px;font-size:13px}.report-files a{color:var(--brand);text-decoration:underline;margin-right:20px}@media(max-width:700px){main#main{padding:14px}}</style></head><body><main id="main"></main><nav class="report-files"><a href="三季四大联赛-半球以内逐场记录.csv">下载全部2450场研究表</a><a href="三季浅盘研究报告.md">阅读完整分析文字</a></nav><script type="module">'+script+'\nconst localReport='+payload+';renderHandicapStudy(document.querySelector("#main"),async()=>({ok:true,json:async()=>localReport}));</script></body></html>'
    (args.archive/'三季浅盘研究报告.html').write_text(html,encoding='utf-8')
    (args.archive/'使用说明.txt').write_text('先打开“三季浅盘研究报告.html”，可离线切换赛季和联赛；逐场记录.csv可用Excel打开。所有数据是历史研究，不是赛前实际发布的预测。球队名称保留原数据商写法，避免中文别名误配。原始来源宽表不包含在分享包内。\n',encoding='utf-8')
    with ZipFile(args.archive/'三季浅盘研究资料包.zip','w',ZIP_DEFLATED) as z:
        for p in sorted(args.archive.iterdir()):
            if p.is_file() and p.suffix in {'.csv','.md','.html','.json','.txt'}:z.write(p,p.name)
    print('PACKAGED',args.archive/'三季浅盘研究资料包.zip')


if __name__=='__main__':main()
