import {data,names,history,liveStatus} from './repository.mjs';
import {main,esc,monogram,formRun,pageHeading,sourceLink} from './ui.mjs';
import {timestamp} from './football-components.mjs';
import {league} from './league.mjs';
import {addedSourceSections,loadOfficialChecks} from './source-panel.mjs';
export function renderTeams() {
  main.innerHTML = `${pageHeading(`${league.name} · ${league.countLabel}支球队`, '选择一支球队，查看球员与最近二十场比赛表现。', `<span class="tag">${esc(data.season)}</span>`)}
    <div class="toolbar"><div class="search"><input id="team-search" type="search" placeholder="搜索球队中文名、英文名或缩写" aria-label="搜索球队"></div><span class="search-count" id="team-count">共 ${data.teams.length} 支球队</span></div>
    <div class="team-grid">${data.teams.map(t => `<a class="team-card" href="#/team/${t.id}" data-team-search="${esc([t.cn,t.name,t.short].join(' ').toLowerCase())}"><div class="team-card-top">${monogram(t)}<span class="enter" aria-hidden="true">↗</span></div><h2>${esc(t.cn)}</h2><p>${esc(t.name)}</p><div class="team-card-bottom"><span>${data.players.filter(p => p.team === t.id).length} 位球员</span><span class="form-run" aria-label="最近五场，最新在左">${formRun(t)}</span></div></a>`).join('')}</div>
    <div id="team-empty" class="empty hidden">没有找到这支球队，试试英文名或其他关键词。</div>
    <p class="note">球员名单来自 ${league.roster}；战绩标记由左至右从新到旧。</p>`;
  document.querySelector('#team-search').addEventListener('input', event => {
    const search = event.target.value.trim().toLowerCase();
    let count = 0;
    for (const card of main.querySelectorAll('[data-team-search]')) {
      const show = card.dataset.teamSearch.includes(search);
      card.classList.toggle('hidden', !show); if (show) count++;
    }
    document.querySelector('#team-count').textContent = `找到 ${count} 支球队`;
    document.querySelector('#team-empty').classList.toggle('hidden', count > 0);
  });
}

export function renderSources() {
 const status=liveStatus();
 main.innerHTML=`${pageHeading('资料来源与更新','查看比赛、球员、译名和分析的统计口径。')}<article class="prose"><div class="notice">${esc(status.text)} · 最近成功：${esc(status.stamp)}。当前查看${league.name} ${data.teams.length} 队，可通过赛事入口切换英超、西甲、意甲、德甲与欧冠。</div>
 <h2>比赛、球员与赔率</h2><p>${league.id==='ucl'?'欧冠球队、球员、赛程与比分来自 ESPN，参赛名单与 UEFA 官方赛程核对。联赛阶段36队、每队8场，共144场；淘汰赛赛程确定后继续同步。':league.id==='epl'?'球队、球员与本赛季赛程来自英超官方 FPL。':league.id!=='laliga'?'球队、球员、赛程与比分来自 ESPN，历史赛果与赔率来自 Football-Data。':'球队与赛程、比分来自 LALIGA 官方；球员资料来自 ESPN。未提供的球员分钟数留空，未标注伤停不等于确认可以出场。'}比赛与赔率按分钟检查，其他资料依照同步监控内的间隔更新。管理员可暂停或恢复后台同步；暂停后保留已有资料，顶部会显示暂停状态。页面按分钟读取快照。来源中断时保留最近成功的数据，并在<a href="#/status">同步监控</a>逐项标明；三分钟未更新比分会显示“待更新”。</p><p>${league.id==='ucl'?'近况显示最近20场已收录正式比赛，可跨赛事、赛季，剔除友谊赛；仅欧冠可单独筛选。比分、胜平负与结算均按90分钟含补时，加时、点球和两回合总比分不计入；无法核对90分钟比分的场次不参与统计。赔率为 ESPN 收录的三项十进制赔率采集快照，覆盖不完整，不代表实时盘口或收盘价。':'最近二十场覆盖已完成的'+league.name+'与'+league.lower+'，可跨赛季。历史赔率来自 Football-Data，优先采用市场平均收盘赔率；当前报价另从 ESPN 公开赛事接口采集，是否有报价取决于来源覆盖。'}支持胜平负、亚洲让球与大小球；比分赔率来源缺失时可手动录入。明确标为开盘和收盘的报价分开展示，历史表的其他早期报价不冒充开盘。逐次变化从本网站首次采集后记录。</p>
 ${addedSourceSections()}<h2>中文与粤语姓名</h2><p>当前 ${data.players.length} 名球员中，${Object.keys(names?.names||{}).length} 名已有大陆与香港名称来源。通过完整出生日期或当前球队名单中的完整英文名核对人物；暂用音译逐项标注，并保留原名。</p><p>香港版采用港式用字与来源中的译名，有出处的条目可查看来源；暂译等待进一步核对。名称库最近检查：${timestamp(names?.updatedAt)}。</p>
 <h2>转会与领队更换</h2><p>收录最近两个赛季公开表格中的变动，分开标记转会、自由转会与租借，并保留来源。部分条目仅提供转会窗口或赛季，按来源显示，不推定具体生效日期。领队资料包含临时任命；未来上任日期会明确标记。每 60 秒检查，实际更新受公告发布和资料源整理速度影响。</p><p>最近检查：${timestamp(history?.updatedAt)}。${history?.sources?.some(s=>!s.ok)?'部分来源最近未成功读取，相关记录沿用旧快照。':'来源检查情况可在下方逐项查看。'}</p>
 <h2>本地模型辅助分析</h2><p>本地模块根据历史进失球、主客场与样本收缩计算独立泊松概率。DeepSeek 按本地分析规范，结合比赛与人员资料生成两三段结论；数据依据、计算方法和命中率记录在“更多详细资料”中查看。</p><p>90 分钟胜平负命中率以 38% 为检验目标。本地模型逐场历史回测与 DeepSeek 首次赛前预测分开统计，完赛后核对实际结果。管理员只需在后台填写 DeepSeek API 密钥，密钥保存在服务器。</p>
 <h2>新闻、直播与俱乐部背景</h2><p>新闻展示来源标题、时间与原文链接，英文标题在已配置 DeepSeek 时生成中文译文。直播入口链接至官方服务与节目表，地区、账号及本场转播安排以对应平台为准。俱乐部背景按资料来源整理；财务数字标明报告期和币种，未公开的数据留空。对手近况由已收录的交锋计算，不代表未来必然结果。</p><h2>港股与全球行情</h2><p>港股目录来自港交所证券名单，包含主板、GEM 和 REIT 交易柜台；恒指成份股另行标注。参考报价来自腾讯行情，复权历史价格来自东方财富，Yahoo Finance 作为备用来源。黄金与原油期货报价来自 TradingView（通常延迟 10 分钟），比特币来自 Coinbase；价格时间、采集时间与单位分别标注。公司资料、披露权益及报表来自东方财富，并提供港交所公告入口；股东归属权益可能重复，不能直接相加。公司资料每天检查，股价历史每小时检查。</p><p>股票分析由 DeepSeek 根据本地规则和有时间标记的资料生成，每天每只股票保留一份。预测发布日之后首个交易日收盘作为基准，再按 5 或 63 个交易日的复权收盘收益验证。所有到期结果计入命中率，尚未有结果时显示等待验证。</p><h2>个人记录与管理员账号</h2><p>赔率录入与模拟投注保存在当前浏览器，使用虚拟资金。可导出、导入备份转移设备；管理员登录不会自动同步个人模拟记录。初始虚拟资金 10,000，已知赛果的模拟标记为历史回测。目前没有会员收费、手机绑定或支付功能。</p>
 <h2>来源与署名</h2><ul class="source-list">${data.sources.map(s=>`<li>${sourceLink(s.url,s.name)}<span>获取时间：${timestamp(s.fetchedAt)}</span></li>`).join('')}<li>${sourceLink('https://www.football-data.co.uk/notes.txt','Football-Data 字段与赔率说明')}</li>${(history?.sources||[]).map(s=>`<li>${sourceLink(s.url,decodeURIComponent(s.url.split('/').pop()).replaceAll('_',' '))}<span>${s.ok?'最近检查成功':'最近检查未成功'} · ${timestamp(s.checkedAt)}</span></li>`).join('')}<li>${sourceLink('https://www.wikipedia.org/','Wikipedia 贡献者')} · ${sourceLink('https://creativecommons.org/licenses/by-sa/4.0/','CC BY-SA 4.0')}<span>姓名变体、转会与领队资料经过摘录和结构化整理；每条记录尽可能保留公告来源。</span></li></ul></article>`;
 loadOfficialChecks();
}
