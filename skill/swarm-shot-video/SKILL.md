---
name: swarm-shot-video
description: 用 Swarm 光标引擎把任意页面做成「拆解 + 重建」两幕视频（虚拟时钟录制、转场合成、事件音效），用于做集群光标与页面拆解类演示视频
---

# SwarmShot 操作手册

把任意页面处理成两幕视频：集群光标先把页面拆成块搬离，再按同一份蓝图重建，录制走虚拟时钟，帧序列可复现

仓库：https://github.com/lujun-dev/swarmshot

## 环境

Node 18+、Chrome、ffmpeg、Python 3

```
git clone https://github.com/lujun-dev/swarmshot
cd swarmshot
```

## 选页面

`swarm.js` 在点击瞬间遍历 DOM 生成蓝图，因此页面需满足

- 首屏可独立切块的元素 15 个以上（标题、卡片、按钮、图），否则拆解层次不足
- 无固定定位的 cookie 横幅或订阅弹窗，固定元素会作为单块整体搬走
- 字体同源或为系统字体，跨域字体会在截图阶段缺失
- 正文高度大于视口，否则构建阶段会超出可视区

## 拆解幕

```
node tools/swarm-run.mjs https://example.com out/act1 --sec=18 --fps=30 --w=1600 --h=900 --mode=teardown --maxitems=110 --agents=22
```

输出 `out/act1/` 下逐帧 jpg 与 `sfx.json`

## 重建幕

```
node tools/swarm-run.mjs https://example.com out/act2 --sec=26 --fps=30 --w=1600 --h=900 --mode=build --code=1 --speed=2.0 --tour=1 --maxitems=110 --agents=6
```

`--code=1` 开右栏代码窗，`--tour=1` 让光标点击教程卡，`--speed` 控制建设速度

## 参数

| Flag | Default | 说明 |
| --- | --- | --- |
| `--sec` | 20 | 时长 |
| `--fps` | 30 | 帧率 |
| `--w` `--h` | 1600 900 | 视口尺寸，即输出分辨率 |
| `--mode` | teardown | `teardown` / `build` |
| `--maxitems` | 110 | 切块上限 |
| `--agents` | 22 | 光标数量，拆解幕 20–24，重建幕 5–8 |
| `--speed` | 1 | 建设速度倍率 |
| `--tour` `--code` | 0 | 教程卡、代码窗 |
| `--wait` | 3000 | 加载后等待，毫秒 |

## 合成

```
python tools/assemble-film.py --a1 out/act1 --a2 out/act2 --out out/film.mp4 --a2tail 2.43 --sfx 0.50 --bgm 0.48 --bgmlp 2000
```

| Flag | Default | 说明 |
| --- | --- | --- |
| `--a2tail` | 0 | 第二幕尾部裁掉的秒数，按片尾空转长度定 |
| `--xfade` | 0.35 | 转场时长 |
| `--sfx` `--bgm` | 0.50 0.48 | 增益 |
| `--bgmlp` | 2000 | BGM 低通截止 |

转场偏移由两幕时长自动计算，异常时用 `--xfade` 覆盖

## 音效

`assemble-film.py` 内置混音链路，独立运行用

```
python tools/audio-events.py out/act1 out/act1/silent.mp4 out/act1/film.mp4
```

`SFX_DROP` 指定丢弃的事件类型，默认 `key`，事件表为 JSON 数组，每条含时间、类型与光标坐标，类型到采样与增益的映射在 `audio-events.py` 顶部

响度链路为两遍 `loudnorm linear=true`，单遍动态模式会改变已设定的增益比例，输出目标 −14 LUFS

## 虚拟时钟

`swarm-run.mjs` 覆写 `performance.now`、`Date.now`、`setTimeout`、`requestAnimationFrame`，按 `1000/fps` 推进并调用 `Page.captureScreenshot`，引擎全部动画由 `App.frame(now)` 的 `dt` 驱动，因此每次录制结果一致

事件表时间戳基于同一时钟，不需要额外对齐

## 已知限制

- 视觉重建，不是克隆：动画在点击瞬间冻结，画布、视频、跨域 iframe 降级为占位
- 超长页面约 4,000 层 / 40,000 px 封顶
- 转场用 `xfade`，同一帧叠两层会出现重影
- 录制分辨率即输出分辨率，放大不提升清晰度
- 引擎无许可证，商用前联系原作者

## License

引擎改编自 [DhvanilPatel/swarm-cursors](https://github.com/DhvanilPatel/swarm-cursors)（v1.2.0），上游为 [Joel Califa](https://joelcalifa.com) 的 Swarm，上游无开源许可证，本手册与仓库代码同样不作授权承诺
