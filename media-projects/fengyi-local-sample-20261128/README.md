# 峰弈推荐：本地样片与月度预算

本次是用户授权的本地试做。复用用户已认可的博洛尼亚视频中的两位公仔和暖光房间；更换为利物浦示例对白，保留四轮问答和女生句末「啊」。

## 文件

- `fengyi-local-sample-web.mp4`：17 秒、约 6.2 MB 的快速播放版本，可直接播放或下载。
- `fengyi-local-sample.mp4`：较高码率的本地导出母版。
- `studio/index.html`：可编辑镜头和分轨声音，1344×768、24fps。
- `script.json`、`timeline.json`：台词、音源和镜头时间表。
- `generate_local_voice.py`：参考原片中合成角色声音，使用 Qwen3-TTS 0.6B 在 CPU 上生成新台词。
- `build_sample.py`：组合原声、新对白和原片动作，统一音量；保留原片水印。
- `voice-generation.json`、`asset-provenance.json`：模型版本、耗时和素材校验。
- `composition-check.json`、`speech-check.json`、`media-check.json`、`REVIEW.md`：结构、转写和导出检查。
- `月度视频用量与购买建议.md`、`monthly-budget.json`、`monthly-budget.csv`：数量、公式、价格来源和采购建议。

## 已知限制

这是本地声音与剪辑测试，不是新生成的人物表演。对白长度对应原片动作的重新剪接和轻微变速，尚未实现逐字口型同步。自动语音识别用于检查内容，不能替代对语气自然度的听审。

这条视频未发布至投资网站，也不计入推荐或命中率。示例所引盘口来自已保存的推荐收据，不能当作实时最新报价。

## 本机制作

本机为 i7-13700H、32GB RAM、Intel UHD，没有 NVIDIA GPU。模型与隔离 Python 环境放在 `D:/Codex-local-video-tools/fengyi-20261128/`，避免占满 C 盘；这些大型依赖不会提交 GitHub。模型下载一次后可复用，本次没有付费生成或购买。

使用 Python 3.12、`qwen-tts==0.1.1`、CPU 版 torch、soundfile；检查工具另需 faster-whisper。模型版本固定记录在 `voice-generation.json`。运行前把 `FENGYI_MODEL_CACHE` 指向模型缓存目录。`generate_local_voice.py` 完成后运行 `build_sample.py`。本机 HyperFrames 启动器位于 `C:/Users/acer/.agents/skills/hyperframes/scripts/plugin-cli.mjs`；在 studio 目录运行该启动器的 check、preview、render 命令。渲染缓存也应指向 D 盘。

## 采购原则

每月按 60–80 条成片规划，4 轮问答约 20 秒，并预留 30% 重做预算。月费套餐与自动制作 API 余额不能混用。先看样片；若购买，先按月或小额测试，不先买年付。具体金额与条件见预算文件。
