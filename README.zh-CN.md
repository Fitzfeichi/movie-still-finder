# movie-still-finder · 中文说明

![Python](https://img.shields.io/badge/Python-3.9%2B-3776AB)
![License](https://img.shields.io/badge/License-MIT-blue)
![Version](https://img.shields.io/badge/Version-1.1.0-blue)
![No credentials](https://img.shields.io/badge/Credentials-none-brightgreen)

一个**不挑 AI agent** 的开源技能：给一句场景描述、一种情绪，或一句台词，帮你找到真实、可溯源、经过视觉复核的电影剧照，用来给文章配图或做封面。

[English README](README.md)

## 什么时候用

需要一张**真实、可溯源**的图来给文字配图（而不是 AI 生成的图）时用：

- *"找一张两个人吵完架后相对无言的剧照。"*
- *"我要某角色说某句台词的那一帧。"*（先核实台词是否真的存在）
- *"给这篇文章配一张剧照 / 封面。"*
- *"核实这句台词是不是真的出现在电影里。"*

## 它解决什么问题

不存在「输入一句自然语言，直接返回那张剧照」的免费公开 API，带原生台词字幕的更是没有。语义搜剧照站基本都要登录、付费或请求签名。真正能跑通的，是一条**组合管线**：

```
需求 → 事实核查 → 选源 → 批量抓候选 → 编号拼图 → 视觉挑帧
     → 取高清原图 → 裁字幕 / 叠字幕 → 视觉复核 → 交付 + 记来源
```

其中「编号拼图 + 视觉挑帧」是关键：把检索问题变成选择题，让视觉模型或人眼一次性看几十张，纯靠文件名和文字猜必错。这个项目把这套管线、以及跑通过程中攒下的踩坑记录，打包成任何 agent 都能用的 `SKILL.md` + 脚本 + 参考手册。

## 特点

- **零登录、零密钥、零付费**：只依赖 Python 3.9+ 和 Pillow，其余全用标准库。需要登录 / 签名 / 付费的工具只写成可选适配说明，不作为依赖。
- **不绑定平台**：遵循 Agent Skills 开放格式（YAML frontmatter + 渐进式披露）。Claude Code、Cursor、Codex、WorkBuddy、Gemini CLI 或任何能读 `SKILL.md` 并执行 shell 的 agent 都能用。
- **不挑系统**：无本机绝对路径、无写死的 Python 解释器、无项目私有台账。字体、输出目录、并发数都运行时解析。
- **仓库内没有任何真实剧照**：测试图是运行时用 Pillow 合成的。代码是 MIT，代码帮你找到的图不是。

## 安装

```bash
# 克隆你自己的 fork（或把整个文件夹复制到 skills 目录）后：
cd movie-still-finder
python -m pip install -r requirements.txt
python scripts/still.py --help
```

当作 skill 用：把整个目录放进你的 agent 的 skills 目录（例如 `~/.claude/skills/movie-still-finder/`、`.workbuddy/skills/movie-still-finder/`），或直接把 `SKILL.md` 指给 agent。无需构建、无需注册。

## 五分钟上手

先跑 `probe`：数据源可用性会变，今天能连的站明天可能返回 502。想完全不联网也能跑通，见 [quickstart.md](examples/quickstart.md) 的离线自检一节。

```bash
# 1. 先探测：当前环境哪些源能连通（免费、免登录）
python scripts/still.py probe

# 2. 从实测可达的画廊页批量抓候选
#    --image-referer 用站点根，图片 CDN 通常不接受文章页 URL 当 Referer
python scripts/still.py grab --out ./work \
  --page "https://movie-screencaps.com/avatar-2009/page/114" \
  --image-referer "https://movie-screencaps.com/" --limit 40
#   产出：work/candidates/、work/contact_1.jpg、work/manifest.json

# 3. 打开 contact_1.jpg（人眼或视觉模型），记下选中的编号
# 4. 处理选中帧并交付
python scripts/still.py crop work/candidates/p1_02.jpg --bottom 100 -o work/clean.jpg
python scripts/still.py deliver ./work --picks examples/sample-picks.json --out ./delivery
```

`grab` 会写出 `candidates/`、编号拼图和 `manifest.json`（来源页、图片直链、尺寸、时间），任何候选都不会被删除。这个示例页开头是片头卡，拼图里会有几张装饰图——这正说明为什么视觉挑帧不能省。交付时若出现 `min_width` 警告也属正常：缩略图画廊的图偏小，用 `full` 取选中帧的高清原图即可。

台词型需求用 `quote` 拿影片 + 毫秒时间点：

```bash
python scripts/still.py quote "I see you" --title Avatar
```

完整示例见 [examples/quickstart.md](examples/quickstart.md)，命令说明见 `scripts/still.py --help`。

## 可选配置（profiles）

默认是 `profiles/minimal.json`：通用最小流程，不替你决定选图方式。个人化的编辑偏好是**可选配置**，不是内置政策：

```bash
python scripts/still.py rules --profile profiles/editorial-wechat.json
python scripts/still.py deliver ./work --picks picks.json \
  --profile profiles/editorial-wechat.json --out ./delivery
```

`editorial-wechat.json` 打包了一套中文长文编辑习惯：编号预览由人选图（不自动定稿）、**精选 + 全量双文件夹且不删任何候选**、强制事实核查、字幕与来源必须标注、2.35:1 封面试裁对比图、避免多张图来自同一部片。字段含义见 [profiles/README.md](profiles/README.md)。

注意：记录来源、标注合成字幕、不删除任何文件、不编造图片链接是**代码层的硬规则**，profile 只能加码、不能关掉。

## 目录

| 路径 | 内容 |
|---|---|
| `SKILL.md` | agent 入口，主文件保持精简，细节按需跳转 |
| `scripts/` | 统一 CLI 与库函数 |
| `references/` | 端到端 SOP、数据源优先级、约 30 条踩坑、事实核查案例、图像处理手法、版权边界、梗图附录、可选适配器 |
| `profiles/` | 可选行为配置（JSON，标准库即可解析） |
| `examples/` | 上手示例、示例需求、示例选图清单 |
| `tests/` | 离线端到端测试 + 可移植性 / 脱敏扫描 |
| `docs/iterations/` | 三轮自检报告；[最终报告（中文）](docs/iterations/final-report.zh-CN.md) 与英文版 |

## 数据源速览

| 优先级 | 源 | 适合 |
|---|---|---|
| ★★★ | FilmGrab 精选帧画廊 | 干净、宽幅、无字幕的封面帧 |
| ★★★ | 带图注的影评 / 公众号文章 | 场景与情绪语义；图注等于人工标注 |
| ★★☆ | 逐帧截图库 | 按帧号取精确画面，多为商业院线片 |
| ★★☆ | 公开台词检索接口 | 台词 → 影片 + 毫秒时间点 |
| ★☆☆ | 通用图片搜索 | 语义漂移严重，必须视觉复核 |

具体参数、必需的 `Referer`、已失效站点清单见 [references/sources.md](references/sources.md) 与 [references/pitfalls.md](references/pitfalls.md)。

## 三条最容易踩的坑

1. **先做事实核查**。网上流传的「某某片里男主说了这句」经常是二次概括，那帧根本不存在（档案里有两个真实案例）。
2. **别在 403 上死磕**。付费站、签名站、反爬站直接换源，不要用等效手段绕过，也不要循环重试。
3. **字幕要标明是否合成**。叠加的台词字幕不是影片原生画面，交付说明里必须写清。

## 版权

本仓库不含任何影片截图。逐帧截图库、影评配图、宣传剧照的权利归片方 / 站点所有；下载用于个人学习或文章草稿，不等于获得公开发布或二次分发的授权。发布前请读 [references/delivery.md](references/delivery.md)。

## 贡献与许可

最有价值的贡献是「新失效的源」或「新跑通的源」，见 [CONTRIBUTING.md](CONTRIBUTING.md)。提交前跑 `python tests/test_offline.py` 与 `python tests/test_portability.py`。代码许可 [MIT](LICENSE)。
