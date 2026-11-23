# SwarmShot

驱动 Swarm 光标引擎在一个真实页面上跑完「拆解 → 重建」两幕，用虚拟时钟逐帧录制，再合成为视频

在线看：https://lujun-dev.github.io/swarmshot/

## Credit

引擎改编自 [DhvanilPatel/swarm-cursors](https://github.com/DhvanilPatel/swarm-cursors)（v1.2.0），其上游是 [Joel Califa](https://joelcalifa.com) 的 [Swarm](https://github.com/califa/swarm-site)

光标组、群集物理、构建编排、标尺与整体视觉均来自原作者，这里加上的是把它对准任意页面、以及把一个可复现的录制链路接到它后面

## How it works

1. **Snapshot** — `engine/swarm.js` 遍历 DOM（含 open shadow root），产出蓝图：rect、text layer、pen line、media、master/duplicate、guide
2. **Teardown** — 集群光标从中心出巢，把蓝图切成的块逐块搬离，资源条按块类型计数，扫描期间不染色
3. **Build** — 按同一份蓝图重建，任务自上而下解锁，子块等父块，duplicate 等 master，代码窗行数跟随完成度
4. **Record** — `tools/swarm-run.mjs` 经 CDP 注入引擎，把 `performance.now`、`Date.now`、`setTimeout`、`requestAnimationFrame` 换成虚拟时钟，每 16.67 ms 推一帧并截图
5. **Assemble** — `tools/assemble-film.py` 拼接两幕、加 `xfade` 转场、混音、封装

录制走虚拟时钟，所以帧序列可复现，音效事件表的落点与画面严格对齐

## Files

| Path | What it is |
| --- | --- |
| `engine/manifest.json` | Manifest V3，权限 `activeTab`、`scripting`、`storage` |
| `engine/background.js` | 点击图标 → 媒体截图 → 注入 `swarm.js` |
| `engine/swarm.js` | 快照、渲染与群集引擎，无外部依赖 |
| `engine/autoplay.js`、`options.*` | 自动播放设置 |
| `tools/swarm-run.mjs` | 虚拟时钟录制壳，输出逐帧 jpg 与 `sfx.json` |
| `tools/assemble-film.py` | 两幕拼接、转场、调色、封装 |
| `tools/audio-events.py` | 事件表 → 合成音效与 BGM → 混流 |
| `skill/swarm-shot-video/` | 给 AI 编程工具用的操作手册 |
| `index.html`、`assets/` | 演示页与两版成片 |

## Run

要求 Node 18+、Chrome、ffmpeg、Python 3

```
node tools/swarm-run.mjs https://basecamp.com out/act1 --sec=18 --fps=30 --w=1600 --h=900 --mode=teardown --maxitems=110 --agents=22
node tools/swarm-run.mjs https://basecamp.com out/act2 --sec=26 --fps=30 --w=1600 --h=900 --mode=build --code=1 --speed=2.0 --tour=1 --maxitems=110 --agents=6
python tools/assemble-film.py --a1 out/act1 --a2 out/act2 --out out/film.mp4 --a2tail 2.43 --sfx 0.50 --bgm 0.48 --bgmlp 2000
```

`swarm-run.mjs` 参数

| Flag | Default | 说明 |
| --- | --- | --- |
| `--sec` | 20 | 录制时长，秒 |
| `--fps` | 30 | 帧率，录制分辨率与帧率即输出规格 |
| `--w` `--h` | 1600 900 | 视口尺寸 |
| `--mode` | teardown | `teardown` 拆、`build` 建 |
| `--maxitems` | 110 | 切块上限，过高会让块互相挤压 |
| `--agents` | 22 | 光标数量 |
| `--speed` | 1 | 建设速度倍率 |
| `--tour` | 0 | 光标点击教程卡 |
| `--code` | 0 | 右侧代码窗 |
| `--wait` | 3000 | 页面加载后等待，毫秒 |

`assemble-film.py` 参数

| Flag | Default | 说明 |
| --- | --- | --- |
| `--a1` `--a2` | — | 两幕帧目录 |
| `--a2tail` | 0 | 第二幕尾部裁掉的秒数 |
| `--xfade` | 0.35 | 转场时长 |
| `--sfx` `--bgm` | 0.50 0.48 | 音效与 BGM 增益 |
| `--bgmlp` | 2000 | BGM 低通截止频率 |

`SFX_DROP` 环境变量控制丢弃哪类音效事件，默认 `key`，音效事件由 `sfx.json` 描述，一条事件包含时间、类型与光标方位

## Changes relative to upstream v1.2.0

- 出巢：光标自中心螺旋散开，半径呼吸，约 1 秒完成
- 扫描阶段：横向扫描线带发光，资源条分子置 0、暂不染色
- 资源条：六边形槽位，显示名称与计数，填充只跟分子走
- 代码窗行数绑构建进度（完成比 × 520，上限 80 行/秒）
- 镜头跟随最靠上的未完成任务，速度上限 1150 px/s
- 空转锚点改为视口内随机点，偏离过远时从边缘重新进场
- 新增 `tools/` 录制壳与合成流水线

## Limits

- 视觉重建，不是克隆：动画在点击瞬间冻结，画布、视频、跨域 iframe 降级为占位
- 超长页面约 4,000 层 / 40,000 px 封顶
- 页面正文短于视口时，构建阶段会超出可视区
- 跨域字体在截图中不渲染

## License

None yet. The original Swarm site is published without a license and this project adapts parts of it, so please don't reuse this code without checking with [Joel Califa](https://joelcalifa.com) as well.

与上游一致：无许可证，公开可读，商用前需联系原作者
