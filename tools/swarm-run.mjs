/* swarm-run.mjs — 用原项目（swarm-cursors）的引擎，冻结时间逐帧录制
 *
 * 原理：swarm.js 的动画完全由 App.frame(now) 的 dt 驱动。
 * 我们把 performance.now / Date.now / setTimeout / rAF 换成虚拟时钟，
 * 每「推」16.67ms 就截图一张，于是得到完全可复现的逐帧画面。
 *
 * 用法: node swarm-run.mjs <url> <outdir> [--sec=25] [--fps=60] [--w=1920] [--h=1080]
 */
import fs from 'node:fs/promises';
import { spawn } from 'node:child_process';
import path from 'node:path';

const CHROME = 'C:/Program Files/Google/Chrome/Application/chrome.exe';
const PORT = 9361;
const SWARM = path.resolve('vendor/swarm-cursors/swarm-rebuild/swarm.js');

const argv = process.argv.slice(2);
const url = argv[0];
const outdir = argv[1] || 'out/swarm';
const opt = (k, d) => {
  const hit = argv.find((a) => a.startsWith('--' + k + '='));
  return hit ? Number(hit.split('=')[1]) : d;
};
const SEC = opt('sec', 25), FPS = opt('fps', 60), W = opt('w', 1920), H = opt('h', 1080);
const MODE = (argv.find((a) => a.startsWith('--mode=')) || '--mode=build').split('=')[1];
const SPEED = Number((argv.find((a) => a.startsWith('--speed=')) || '--speed=1').split('=')[1]);
const MAXITEMS = Number((argv.find((a) => a.startsWith('--maxitems=')) || '--maxitems=0').split('=')[1]) || 0;
const TOUR = (argv.find((a) => a.startsWith('--tour=')) || '--tour=0').split('=')[1] === '1';
const CODE = (argv.find((a) => a.startsWith('--code=')) || '--code=0').split('=')[1] === '1';
const AGENTS = opt('agents', 0);
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

if (!url) { console.error('usage: node swarm-run.mjs <url> <outdir> [--sec=25] [--fps=60]'); process.exit(1); }

/* 虚拟时钟：装进页面，替换所有时间源 */
const CLOCK = (__mode__, __speed__, __maxitems__, __tour__, __code__, __agents__) => `
(() => {
  let now = 0, seq = 1;
  const timers = [], rafs = [];
  performance.now = () => now;
  Date.now = () => 1700000000000 + Math.round(now);
  window.setTimeout = (fn, ms = 0, ...a) => { const id = seq++; timers.push({ id, t: now + Math.max(0, ms|0), fn: () => fn(...a) }); return id; };
  window.clearTimeout = (id) => { const i = timers.findIndex(x => x.id === id); if (i >= 0) timers.splice(i, 1); };
  window.setInterval = () => 0;
  window.requestAnimationFrame = (cb) => { const id = seq++; rafs.push({ id, t: now + 16.667, cb }); return id; };
  window.cancelAnimationFrame = (id) => { const i = rafs.findIndex(x => x.id === id); if (i >= 0) rafs.splice(i, 1); };
  window.__vtAdvance = (ms) => {
    const target = now + ms;
    let guard = 0;
    while (guard++ < 400) {
      let pickT = Infinity, pi = -1, pk = '';
      for (let i = 0; i < timers.length; i++) if (timers[i].t < pickT) { pickT = timers[i].t; pi = i; pk = 't'; }
      for (let i = 0; i < rafs.length; i++) if (rafs[i].t < pickT) { pickT = rafs[i].t; pi = i; pk = 'r'; }
      if (pi < 0 || pickT > target) break;
      now = Math.max(now, pickT);
      const item = pk === 't' ? timers.splice(pi, 1)[0] : rafs.splice(pi, 1)[0];
      try { pk === 't' ? item.fn() : item.cb(now); } catch (e) {}
    }
    now = target;
    return { timers: timers.length, rafs: rafs.length };
  };
  window.__vtNow = () => now;
  window.__swarmSfxLog = [];
  window.__swarmMode = ${JSON.stringify(__mode__)};
  window.__speed = ${JSON.stringify(__speed__)};
  window.__maxItems = ${JSON.stringify(__maxitems__)};
  window.__tour = ${JSON.stringify(__tour__)};
  window.__codePanel = ${JSON.stringify(__code__)};
  if (${JSON.stringify(__agents__)} > 0) {
    window.__maxAgents = ${JSON.stringify(__agents__ || 8)};
    window.__minAgents = ${JSON.stringify(Math.min(8, __agents__ || 8))};
    window.__flockAgents = ${JSON.stringify(__agents__ || 8)};
    window.__introAgents = ${JSON.stringify(__agents__ || 8)};
  } else if (String(window.__swarmMode).startsWith("teardown")) {
    window.__maxAgents = 8;
    window.__minAgents = 8;
    window.__flockAgents = 8;
    window.__introAgents = 8;
  }
})();
`;

class CDP {
  constructor(ws) {
    this.ws = ws; this.id = 0; this.pending = new Map();
    ws.onmessage = (e) => {
      const m = JSON.parse(e.data);
      if (m.id && this.pending.has(m.id)) {
        const { res, rej } = this.pending.get(m.id); this.pending.delete(m.id);
        m.error ? rej(new Error(m.error.message)) : res(m.result);
      }
    };
  }
  send(method, params = {}, sessionId) {
    const id = ++this.id;
    const msg = { id, method, params };
    if (sessionId) msg.sessionId = sessionId;
    return new Promise((res, rej) => { this.pending.set(id, { res, rej }); this.ws.send(JSON.stringify(msg)); });
  }
}

async function main() {
  const swarmSrc = await fs.readFile(SWARM, 'utf8');
  await fs.mkdir(outdir, { recursive: true });

  const proc = spawn(CHROME, [
    '--headless=new', '--disable-gpu', '--hide-scrollbars', '--mute-audio',
    '--allow-file-access-from-files', '--force-device-scale-factor=1',
    `--window-size=${W},${H}`, `--remote-debugging-port=${PORT}`,
    '--user-data-dir=D:/hermes/cache/scratch/cdp-swarmrun',
    'about:blank',
  ], { stdio: 'ignore' });

  let wsUrl = null;
  for (let i = 0; i < 100; i++) {
    try { const r = await fetch(`http://127.0.0.1:${PORT}/json/version`); wsUrl = (await r.json()).webSocketDebuggerUrl; break; }
    catch { await sleep(250); }
  }
  if (!wsUrl) throw new Error('chrome failed to start');

  const ws = new WebSocket(wsUrl);
  await new Promise((res, rej) => { ws.onopen = res; ws.onerror = rej; });
  const cdp = new CDP(ws);
  const { targetId } = await cdp.send('Target.createTarget', { url: 'about:blank' });
  const { sessionId } = await cdp.send('Target.attachToTarget', { targetId, flatten: true });
  await cdp.send('Page.enable', {}, sessionId);
  await cdp.send('Runtime.enable', {}, sessionId);
  await cdp.send('Emulation.setDeviceMetricsOverride', { width: W, height: H, deviceScaleFactor: 1, mobile: false }, sessionId);
  // 时钟必须在页面脚本之前装好
  await cdp.send('Page.addScriptToEvaluateOnNewDocument', { source: CLOCK(MODE, SPEED, MAXITEMS, TOUR, CODE, AGENTS) }, sessionId);
  await cdp.send('Page.navigate', { url }, sessionId);
  await sleep(Number((argv.find((a) => a.startsWith('--wait=')) || '--wait=2500').split('=')[1]));

  const ev = async (expr, awaitP = false) => {
    const r = await cdp.send('Runtime.evaluate', { expression: expr, returnByValue: true, awaitPromise: awaitP }, sessionId);
    if (r.exceptionDetails) console.error('[eval]', JSON.stringify(r.exceptionDetails.exception && r.exceptionDetails.exception.description || r.exceptionDetails).slice(0, 300));
    return r.result && r.result.value;
  };

  // 装引擎
  await ev(swarmSrc);
  console.log('[swarm] injected');

  const FD = 1000 / FPS;
  const n = Math.round(SEC * FPS);
  const t0 = Date.now();
  let lastDone = -1, stall = 0, written = 0, doneFinal = 0, totalFinal = 0;
  for (let i = 0; i < n; i++) {
    await ev(`window.__vtAdvance(${FD})`);
    const shot = await cdp.send('Page.captureScreenshot', { format: 'jpeg', quality: 94 }, sessionId);
    await fs.writeFile(`${outdir}/f_${String(i).padStart(5, '0')}.jpg`, Buffer.from(shot.data, 'base64'));
    written = i + 1;

    // 完事就停：连续 90 帧（1.5s）进度不动，说明建完了
    if (i % 10 === 0) {
      const st = await ev('(() => { const a = window.__swarmRebuild && window.__swarmRebuild.app; if (!a || !a.engine) return null; return { d: a.engine.doneCount, t: a.engine.tasks.length, started: !!a.engine.started }; })()');
      if (st && st.started) {
        if (st.d === lastDone) { if (++stall > 9) break; } else { stall = 0; lastDone = st.d; }
        doneFinal = st.d; totalFinal = st.t;
      }
      if (i % 120 === 0) console.log(`[frame] ${i + 1}/${n}  ${doneFinal}/${totalFinal}`);
    }
  }
  try { console.log('[dbg]', await ev('JSON.stringify(window.__dbg||{})')); } catch (x) {}
  try { const e = await ev('window.__lastErr || ""'); if (e) console.log('[page error]', e.slice(0, 300).replace(/\n/g, ' | ')); } catch (x) {}
  console.log(`[swarm] ${written} frames in ${((Date.now() - t0) / 1000).toFixed(1)}s  (${doneFinal}/${totalFinal} layers)`);

  const log = await ev('JSON.stringify(window.__swarmSfxLog || [])');
  await fs.writeFile(path.join(outdir, 'sfx.json'), log || '[]');
  const st = await ev('(() => { const a = window.__swarmRebuild && window.__swarmRebuild.app; return JSON.stringify({ complete: !!(a && a.complete), timing: a && a.timing, done: a && a.engine && a.engine.doneCount, total: a && a.engine && a.engine.tasks.length }); })()');
  console.log('[swarm] state', st);

  await fs.writeFile(path.join(outdir, 'meta.json'), JSON.stringify({ fps: FPS, frames: written, layers: doneFinal, total: totalFinal }, null, 1));
  const args = ['-y', '-loglevel', 'error', '-framerate', String(FPS), '-i', `${outdir}/f_%05d.jpg`,
                '-c:v', 'libx264', '-preset', 'medium', '-crf', '19', '-pix_fmt', 'yuv420p',
                '-frames:v', String(written), `${outdir}/silent.mp4`];
  await new Promise((res, rej) => {
    const p = spawn('ffmpeg', args, { stdio: 'inherit' });
    p.on('exit', (c) => (c === 0 ? res() : rej(new Error('ffmpeg exit ' + c))));
  });
  console.log('[swarm] silent.mp4 ready');
  try { proc.kill(); } catch {}
  process.exit(0);
}

main().catch((e) => { console.error('FAILED', e.message); process.exit(1); });
