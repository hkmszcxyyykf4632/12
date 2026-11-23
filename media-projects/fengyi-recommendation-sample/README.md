# 峰弈推荐三问三答样板

2026 年 11 月 22 日博洛尼亚对乌迪内斯的历史推荐示范，约 11 秒，1280×720、24 fps、H.264 与 AAC 双声道。视频保留原始赛前推荐：博洛尼亚让半球，比分 2:1；不根据实际赛果修改推荐。全片标明历史日期。

## 对白

- 大首领：喂，今晚有什么好料啊？
- 大天使：今晚买博洛尼亚啊。
- 大首领：怎么让啊？
- 大天使：博洛尼亚让乌迪内斯半球啊。
- 大首领：买几比几啊？
- 大天使：二比一啊。

## 可编辑制作工程

`build_scene.py` 创建完整三维场景与两位角色，含嘴型、眨眼、视线、头部与手臂动作；`timing.json` 保存逐句时间和声音幅度。`audio/` 保存本次整句生成的国语配音和混音。男声为 zh-CN-YunxiNeural，女声为 zh-CN-XiaoyiNeural，没有克隆真人声音。

使用 Blender 4.2 在本目录运行 `blender --factory-startup -b --python build_scene.py`，再运行 `blender --factory-startup -b fengyi-hosts.blend --python render_movie.py`。最后用 Python 运行 `assemble.py`（FFmpeg 需要在 PATH 中）。已有配音不必重新生成。字幕使用 Microsoft YaHei；换操作系统时需安装兼容中文字体并核对布局。

动画可重复渲染，不调用 Canva 或 HeyGen 的视频生成服务。改变对白后，须同步更新声音、时间、嘴型、字幕和推荐来源；不能只替换字幕后继续使用旧配音。

## 检查

`qa-report.json` 记录完整解码通过、263 帧均不重复、视频和音轨规格。关键说话画面及结尾字幕已检查。`speech-transcription.json` 是独立机器转录；球队专名存在同音转录误差，不能当作人工试听或自然程度评分。未声称完成人工听审。

## 发布

`release-manifest.json` 记录视频与封面的大小和 SHA-256。`publish_sample.py --revision <完整提交号>` 在既有投资站服务器执行，先核对固定提交中的媒体文件，再备份目录并新增本样板。它不重新部署应用、不重启采集任务，也不删除旧视频。
