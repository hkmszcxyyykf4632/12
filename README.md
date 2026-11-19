# 峰弈科技 · 体育与市场资料分析

投资与体育网站：**[inwesting.shop](https://inwesting.shop)**；经藏文化：**[tripitaka.shop](https://tripitaka.shop)**。原 [footballknow.art](https://footballknow.art) 保留访问。这份仓库保存网站源码、公开数据快照、需求与设计记录、可见对话归档，以及运行、腾讯云部署和维护说明。

2026-11-19 域名分站：投资与体育网站继续使用原服务器；经藏文化独立部署到香港 2 核、4GB 服务器。两个网站保留互相访问入口。配置与恢复步骤见[独立域名与文化站部署](docs/2026-11-19-独立域名与文化站部署.md)。

2026-11-19 更新：马匹每条有效往绩增加官方赛事回放入口；左侧新增“经藏文化”，提供独立的[经藏阅读网站](https://footballknow.art/jingzang/)，保留上传包中的 54 部书籍、简繁切换和阅读功能。验证与发布记录见[马匹回放与经藏文化](docs/2026-11-19-马匹回放与经藏文化.md)。

2026-11-17 新增：港股现金多（绿色）／负债多（红色）分类、主席履历与已核实照片、52 周高低位和每日涨跌榜；球队主客场亚洲盘走势图；马匹晨操、步速、往绩评语与官方直播入口；各项目长篇研究规范、固定原预测及赛后／收盘复盘；美元指数与央行利率。详见[研究复盘与财务分类](docs/2026-11-17-研究复盘与财务分类.md)。

新版首页设有财经、足球、赛马中文新闻与来源配图；品牌使用圆形双行“峰弈／科技”。新增[马匹分类](https://footballknow.art/#/horses)、[骑师与练马师榜](https://footballknow.art/#/racing-rankings)、赛马日出赛分组、独赢／位置／连赢报价。详见[本轮扩展与验证](docs/峰弈科技新闻与赛马扩展.md)。

本轮在 Kyle 企业版 V2 基础上加入意甲、德甲、五项赛事合并赛程、新闻、俱乐部背景、扩展盘口、全港股与全球行情、香港赛马、赞助商介绍，以及管理员暂停／恢复同步。最新股票与赛马覆盖及验证见[香港赛马与全港股](docs/香港赛马与全港股上线记录.md)，较早扩展见[五赛事、行情与同步控制](docs/五赛事行情与同步控制.md)。

来源实际状态以[同步监控](https://footballknow.art/#/status)为准；暂停时保留最近资料，恢复后默认最多同时运行 2 项后台任务。数据缺项、报价时间、财报币种和预测到期数量均在对应页面展示。

## 网站入口

| 赛事 | 球队 | 排名 | 比赛 |
| --- | --- | --- | --- |
| 英超 | [20 支球队](https://footballknow.art/#/teams) | [数据榜单](https://footballknow.art/#/rankings) | [比赛中心](https://footballknow.art/#/matches) |
| 西甲 | [20 支球队](https://footballknow.art/?league=laliga#/teams) | [数据榜单](https://footballknow.art/?league=laliga#/rankings) | [比赛中心](https://footballknow.art/?league=laliga#/matches) |
| 意甲 | [20 支球队](https://footballknow.art/?league=seriea#/teams) | [数据榜单](https://footballknow.art/?league=seriea#/rankings) | [比赛中心](https://footballknow.art/?league=seriea#/matches) |
| 德甲 | [18 支球队](https://footballknow.art/?league=bundesliga#/teams) | [数据榜单](https://footballknow.art/?league=bundesliga#/rankings) | [比赛中心](https://footballknow.art/?league=bundesliga#/matches) |
| 欧冠 | [36 支联赛阶段球队](https://footballknow.art/?league=ucl#/teams) | [数据榜单](https://footballknow.art/?league=ucl#/rankings) | [比赛中心](https://footballknow.art/?league=ucl#/matches) |

球员档案提供普通话与粤语名称，保留原名与译名来源；球队页有最近二十场、转会和领队更换。数据中心有总榜、主客场与近况榜、射手、助攻及球队指标。比赛详情显示已取得的首发、替补、换人、阵型位置分组、事件、统计、此前交锋与多家公司赔率快照。关注球队和模拟记录保存在当前浏览器。

DeepSeek 使用本地统计、详细分析规范与实际历史阵容整理下一场：默认两至三段结论，展开后查看细节。后台只需输入 API 密钥。38% 是 90 分钟胜平负的检验目标，当前没有完成本地大模型训练或宣称达到固定预测命中率。微信支付和付费会员按用户最新决定暂缓，保留两个管理员。

新增入口：[五项赛事即场比赛](https://footballknow.art/#/live) · [球队新闻](https://footballknow.art/#/news) · [全部港股与全球行情](https://footballknow.art/#/markets) · [香港赛马](https://footballknow.art/#/racing) · [马匹血统与往绩示例](https://footballknow.art/#/horse/HK_2023_J463) · [赞助商](https://footballknow.art/#/sponsors) · [同步开关](https://footballknow.art/#/admin)。

港股目录包含 2,825 个股票及 REIT 交易柜台（2026-11-17），股票名称使用绿色；公司业务、股东、资产负债及复权价格按需获取。香港赛马目录包含 1,466 匹现役马匹，提供父母系与外祖父、近三季往绩和按实际出赛计算的场地表现；赛前预测与赛后评价分开保存，原始预测不可覆盖。

## 从哪里开始

- [项目现状与全部需求](docs/项目现状与需求.md)
- [完整可见对话记录](docs/对话记录.md) · [机器可读版本](docs/对话记录.json)
- [本地运行与日常操作](docs/运行与使用.md)
- [腾讯云部署、更新与恢复](docs/腾讯云部署与恢复.md)
- [架构、数据来源及分析方法](docs/架构与数据来源.md)
- [维护、扩展及验证](docs/维护与验证.md)
- [源码](footballknow/) · [详细 AI 分析规范](footballknow/analysis-rules.txt) · [设计约定](footballknow/DESIGN.md)
- [本次 V2 发布验证](docs/企业版V2发布验证.md) · [企业版 V1 发布验证](docs/企业版发布验证.md) · [更早发布记录](docs/发布验证.md)

仓库为公开仓库。账号密码、DeepSeek 密钥、会话、私人预测与账号数据库不随源码上传；现有线上配置继续保存在服务器私密目录。数据快照会过期，网站使用后台任务持续检查来源，界面展示实际取得时间。第三方数据来源与署名保留在页面和 JSON 内；本仓库没有额外授予第三方数据、图片或商标的使用权。
