# Imitate English MVP

一个面向英语启蒙听力的单页 Web MVP。当前内容基于 Peppa Pig S01E01-E10,核心目标是通过“图像 + 声音 + 场景”建立听力锚点,而不是先教拼写和阅读。

## 当前能力

- 10 集片单
- L1 单词图音卡
- L2 短语 / chunk 听辨
- L3 关键句听辨与原片切片
- 整集视频挑战
- 本地/单用户学习进度保存 API
- 全局词库与单集词库

## 数据结构

每集有一个 `lesson-peppa-s01eXX.json`:

- `words`: 当前用于 UI 和出题的 L1 卡片词
- `episode_words`: 本集剧情涉及的关键词,包括复现词
- `new_words`: 相对前序集新增的词
- `reused_words`: 本集复现的已出现词
- `chunks`: L2 短语
- `sentences`: L3 关键句

`lessons.json` 是片单索引。

## 运行

静态文件可直接用任意 HTTP server 托管。若需要保存进度,同时运行 `server.py` 并把前端同源的 `/api/` 请求转发到它。

```bash
python3 server.py
```

`server.py` 默认只监听本机地址,状态文件路径和端口都可用环境变量覆盖:

```bash
STATE_FILE=./data/state.json PORT=8000 python3 server.py
```

## 生成素材

生成图片和 TTS 需要自行提供环境变量。不要提交真实 key。

```bash
cp .env.example .env
```

主要脚本:

- `parse_vtt.py`: 解析 VTT 字幕,生成词频和 transcript
- `gen_episode.py`: 生成图片和 TTS
- `cut_clips.py`: 切 L3 原片音频
- `build_lesson.py`: 构建 lesson JSON
- `convert_to_webp.sh`: PNG 转 WebP

## 目录

```text
assets/                    # 运行所需媒体资源
specs/                     # 每集内容规格
lesson-peppa-s01e*.json    # 每集 lesson 数据
lessons.json               # 片单
index.html                 # 前端
server.py                  # 简单状态 API
```

本地中间产物、原始源视频、归档和 PNG 原图不进入仓库。

## 注意

这是 MVP,不是完整产品。E03-E10 的 L3 时间戳是批量初版,后续可逐集精修。
