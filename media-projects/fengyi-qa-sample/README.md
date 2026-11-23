# 峰弈粤语动态问答样板

大首领提问、大天使回答：「预测错了，复盘看什么？」约 59 秒，1920×1080，30 fps。

本样板是按站长提出的复盘要求整理的示例对白，不是某场赛事的实录或预测。

## 可编辑内容
- `script.json`：对白、字幕、角色和主题段落。
- `make_audio.py`：重做粤语配音并生成声音能量与时间数据。已有音轨可直接使用。
- `build_film.py`：把对白与动画生成到 `film/index.html`。
- `film/assets/expressions.png`：夸张表情；`characters.png`：眨眼素材。
- `film/REVIEW.md`：审看结果与限制。

在 Windows 上，将本机合法安装的 `C:/Windows/Fonts/msyh.ttc` 复制到 `film/assets/fonts/chinese.ttc`（字体不随仓库分发），然后运行 `python build_film.py`。在 film 目录用 HyperFrames 0.9.85 预览或渲染。

发布视频：`footballknow/public/media/videos/fengyi-qa-cantonese-v1.mp4`。只上架视频素材及视频目录记录，不改动现有应用和采集任务。

角色参考由用户指定为 THE MONSTERS 大首领 / Angel in Clouds；图片素材为本次生成的动画素材，不表示 POP MART 官方合作。
