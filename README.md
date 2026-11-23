# SwarmShot

20 个模拟光标把一个真实网站拆成零件，再按同一份结构原样拼回去。全程序化生成，逐帧录制，没有加速。

在线看：https://lujun-dev.github.io/swarmshot/

## 内容

- `index.html` — 作品页（两个视频 + 说明）
- `assets/swarm-16x9.mp4` — 横屏完整版，30 秒
- `assets/swarm-9x16.mp4` — 竖屏版，24 秒

## 说明

- 演示对象是 basecamp.com 的公开页面，只读取结构、不修改对方站点。
- 画面由 Canvas 逐帧渲染后录制，时钟由录制器驱动，因此音效落点与画面同步。
- 两个视频均为一次录制的成片，未做变速处理。
