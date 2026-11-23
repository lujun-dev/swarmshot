# SwarmShot

20 个模拟光标把一个真实网站拆成零件，再按同一份结构原样拼回去。全程序化生成，逐帧录制，没有加速。

在线看：https://lujun-dev.github.io/swarmshot/

## 来源与授权（先看这段）

这个仓库的**动画引擎不是从零写的**。它改编自：

- [DhvanilPatel/swarm-cursors](https://github.com/DhvanilPatel/swarm-cursors)（Chrome 扩展 Swarm Rebuild，v1.2.0）
- 上游再往上是 [Joel Califa](https://joelcalifa.com) 的 Swarm 站点

**上游没有开源许可证。** DhvanilPatel 在 README 里写得很清楚：

> License: None yet. The original Swarm site is published without a license and this project adapts parts of it, so please don't reuse this code without checking with Joel Califa as well.

本仓库保持和上游一样的姿态：**公开可读、免费，但不作任何授权承诺**。想商业使用，请先联系上面两位作者。

我在它上面做的改动见下面「我改了什么」。

## 目录

```
index.html          作品页（两版成片）
assets/             成片：swarm-16x9.mp4（30s）/ swarm-9x16.mp4（24s）
engine/             改编后的 Swarm 引擎（可直接当 Chrome 扩展加载）
tools/
  swarm-run.mjs     虚拟时钟逐帧录制壳
  assemble-film.py  两幕拼接 + 转场 + 出片
  audio-events.py   事件表 → 音效/BGM 混音 → 封装
```

## 怎么跑

要求：Node 18+、Chrome、ffmpeg、Python 3。

1）录第一幕（拆）

```
node tools/swarm-run.mjs https://basecamp.com out/act1 --sec=18 --fps=30 --w=1600 --h=900 --mode=teardown --maxitems=110 --agents=22
```

2）录第二幕（重建）

```
node tools/swarm-run.mjs https://basecamp.com out/act2 --sec=26 --fps=30 --w=1600 --h=900 --mode=build --code=1 --speed=2.0 --tour=1 --maxitems=110 --agents=6
```

3）合成

```
python tools/assemble-film.py --a1 out/act1 --a2 out/act2 --out out/film.mp4 --a2tail 2.43 --sfx 0.50 --bgm 0.48 --bgmlp 2000
```

引擎原理：`swarm.js` 的动画全部由 `App.frame(now)` 的 `dt` 驱动。录制壳把 `performance.now / Date.now / setTimeout / requestAnimationFrame` 换成虚拟时钟，每推 16.67ms 截一帧，所以画面完全可复现，音效落点也能精确对齐。

## 我改了什么（相对上游 v1.2.0）

- 第一幕「出巢」：光标从中心螺旋散开，半径呼吸，约 1 秒完成
- 扫描阶段：横向扫描线带发光，扫描时资源条分子为 0、不染色
- 资源条：六边形槽位 + 名称/计数，扫描中填充只跟分子走
- 第二幕：代码窗行数绑构建进度（`done/total × 520` 行，最高 80 行/秒）
- 镜头跟随：跟着最靠上的未完成任务走，速度上限 1150px/s
- 光标空转：锚点改为视口内随机点，偏离过远从边缘重新进场
- 录制壳与合成流水线（`tools/` 三个文件）为新增

## 成片

- 横屏 30 秒：https://lujun-dev.github.io/swarmshot/assets/swarm-16x9.mp4
- 竖屏 24 秒：https://lujun-dev.github.io/swarmshot/assets/swarm-9x16.mp4

演示对象是 basecamp.com 的公开页面，只读取页面结构，不修改对方站点。
