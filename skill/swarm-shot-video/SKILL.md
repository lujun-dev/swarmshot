---
name: swarm-shot-video
description: 用 swarm 光标引擎把任意网站做成"拆解 + 重建"演示视频（两幕录制、逐帧合成、音效对齐）。Use when 要做光标集群/网站拆解类演示视频。
---

# SwarmShot：网站拆解演示视频

把任意一个真实网页变成"被 20 个光标拆成零件、再原样拼回去"的演示视频。全程序化、逐帧录制、可复现。

仓库：https://github.com/lujun-dev/swarmshot

> 授权说明：引擎改编自 [DhvanilPatel/swarm-cursors](https://github.com/DhvanilPatel/swarm-cursors)，上游是 [Joel Califa](https://joelcalifa.com) 的 Swarm，两者均无开源许可证。免费、公开可读，不构成任何商业授权；商用请先联系上面两位作者。

## 前置

- Node 18+、Chrome、ffmpeg、Python 3
- `git clone https://github.com/lujun-dev/swarmshot`，所有命令在仓库根目录执行
- `engine/` 不需要装成扩展：录制壳会把 `engine/swarm.js` 直接注入页面

## 第 0 步：选目标页（决定了成片好不好看）

挑**首屏内容密集**的页面（产品首页、文档首页）。三个硬条件：

- 首屏有 15 个以上可独立的块（标题、卡片、按钮、图），否则拆不出层次
- 没有 cookie 横幅 / 订阅弹窗（会被当成一块资源搬走，很难看）
- 字体是系统字体或允许跨域，否则截图里会掉字体

## 第 1 步：录第一幕（拆）

```
node tools/swarm-run.mjs https://basecamp.com out/act1 \
  --sec=18 --fps=30 --w=1600 --h=900 \
  --mode=teardown --maxitems=110 --agents=22
```

- `--agents` 光标数量：拆 20–24，建 5–8（人太多画面会乱）
- `--maxitems` 拆成多少块：80–120，超过 150 会挤成一团
- `--mode=teardown` 拆；`--mode=build` 建
- 输出 `out/act1/` 下是逐帧 jpg + `sfx.json`（每个动作的时间点）

## 第 2 步：录第二幕（重建）

```
node tools/swarm-run.mjs https://basecamp.com out/act2 \
  --sec=26 --fps=30 --w=1600 --h=900 \
  --mode=build --code=1 --speed=2.0 --tour=1 --maxitems=110 --agents=6
```

- `--code=1` 开代码窗（右边一边滚代码一边建，视觉信息量大，别关）
- `--speed=2.0` 建设速度，1.6–2.4 之间最好看
- `--tour=1` 让光标偶尔点开教程卡

## 第 3 步：合成

```
python tools/assemble-film.py --a1 out/act1 --a2 out/act2 \
  --out out/film.mp4 --a2tail 2.43 --sfx 0.50 --bgm 0.48 --bgmlp 2000
```

- `--a2tail` 第二幕尾部要砍掉多少秒（结尾光标飞走的空转），看片尾定，一般 1.5–3
- `--sfx/--bgm` 音效与背景音乐比例；0.5 / 0.48 是听感平衡点
- `--bgmlp 2000` BGM 低通，避免和音效抢高频
- 转场偏移自动算，算歪了用 `--xfade=<秒>` 覆盖

## 第 4 步：音效（可选，但很影响观感）

`assemble-film.py` 已内置混音；要改事件表就单独跑：

```
python tools/audio-events.py out/act1 out/act1/film_silent.mp4 out/act1/film_v.mp4
```

- 默认丢掉打字音效（`SFX_DROP=key`）。实测一条 30 秒片 1043 个事件里有 711 个是打字声，全留着"吵得没法看"——这是被明确点名过的坑
- 响度走两遍 `loudnorm linear=true`，单遍动态模式会把改好的配比又压回去
- 成片响度锁 −14 LUFS，真峰值 −1.0 dBFS

## 第 5 步：出片规格

| 平台 | 规格 |
|---|---|
| 源片 | 1920×1080 / 30fps / crf 19（母版约 36 MB / 30 秒） |
| 小红书 | 同上直接发；封面单独从源片抽帧导出 3:4 或 1:1 |
| 抖音 | 优先竖屏重排（9:16，黑底 + 画面居中），否则横屏会被压成小窗 |

竖屏重排：把 16:9 画面等比缩到 1080 宽，贴在 1080×1920 黑底正中，上方留标题区。

## 坑（实测踩过）

1. **前 7 秒全是铺垫 = 完播率死。** 母版开头是页面加载 + 扫描线，抖音实测 2 秒跳出率 49%，完播 3.3%。发竖屏版时从"光标出巢"那一刻起切，别从 0 秒起。
2. **录制分辨率就是成片分辨率。** 1600×900 放大到 1080p 会糊，要 1080p 就直接 `--w=1920 --h=1080`。
3. **页面滚动高度不够会裁。** 目标页正文很短时，第二幕"重建"会超出视口，先手动给页面加高度或换页。
4. **转场不要复制层。** 用 `xfade`，两幕叠化；把同一帧贴两层再淡出，观感是"重影"。
5. **音效密度别靠音量解决。** 吵的根源是事件太密，删打字事件比调小音量有效。
6. **免费发布 ≠ 有授权。** 上游无 LICENSE，公开可以，收费不行。

## 复用别人的仓库时要做的

1. 在自己的 README 顶部写清出处链（DhvanilPatel → Joel Califa）
2. 引用上游那句 "License: None yet … don't reuse this code without checking with Joel Califa" 原文
3. 声明自己的姿态（免费、不作授权承诺、商用联系原作者）
4. 单列一节"我改了什么"，把新增的改动和上游分开
