# 本轮足球推荐视频 · 2026-11-28

沿用用户认可的博洛尼亚原片：暖绿色房间、原来的棕色与白色毛绒角色、原有合成角色声音。四轮问答，保留“喂，今晚有什么好料啊？”、“怎么让啊？”、“买几比几啊？”、“为什么买它啊？”，女方回答尾音“啊”。

13 条成片均已完成；贝蒂斯对巴列卡诺因用户提出澳门盘已让一球而暂停发布，其余 12 条列入发布清单。原推荐全部来自 DraftKings / ESPN，影片标题和描述标明实际来源；不得改名冒充澳门数据。用户现已指定优先参考澳门，官方访问验证尚未完成。不得把另一公司的半球盘与用户报告的澳门一球盘当成同公司变盘。

利物浦成片直接复制已获用户认可的样片，SHA-256 保持相同。该样片口播二比一、零封一球均指利物浦获胜；封存记录按主队在前为 1:2、0:1。其他新片明确口播“主队在前”。页面标题显示实际开赛日期及香港时间。

## 可继续编辑的文件

- `episodes/<event>/script.json`：逐句台词。
- `episodes/<event>/recommendation-receipt.json`：封存推荐身份及赔率来源。
- `episodes/<event>/studio/index.html`、`timeline.json` 和音视频素材：可继续编辑的组合工程。
- `prepare_batch.py`、`generate_voices_batch.py`、`build_episode.py`、`compose_batch.py`、`validate_batch.py`、`render_batch.py`：本地制作与检查流程。
- `publication-holds.json`：暂停上架项目；发布脚本也检查此名单。
- `qa/`、`composition-check.json`、`visual-review.json`、`media-check.json`、`speech-check.json`：实际检查记录。

本轮没有调用付费视频生成服务。Qwen3-TTS 0.6B CPU 模型只生成改动台词，沿用已经认可的人工合成角色参考音；模型与运行环境放在 D 盘，不提交模型到 Git。动作重用原片短段并按新台词时长重定时，属于原片改编，未逐音素重新生成口型。

## 发布

`releases/recommendation-videos-20261128.json` 绑定原推荐的赛事、初版时间、亚洲盘、两个比分与身份。发布脚本检查未开赛、仍为待结算，拒绝不同版本覆盖，备份原索引与视频目录，按固定 Git 提交下载并检查文件散列。播放器保留播放、音量、全屏及下载控件，无自动播放，使用 fast-start MP4。

此目录准备完成不等于已上架；腾讯云部署与公开网页检查结果另记发布回执。赛马下一赛马日尚无已封存的正式推荐，因此未补造推荐视频。
