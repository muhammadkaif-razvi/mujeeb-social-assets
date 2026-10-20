// Story-reel renderer: node render.mjs spec.json out.mp4 [--preview t1,t2,...]
// Renders story.html frame by frame in headless Chromium and pipes JPEG frames to ffmpeg.
import { chromium } from 'playwright-core';
import { spawn } from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const dir = path.dirname(fileURLToPath(import.meta.url));
const [specPath, out, flag, list] = process.argv.slice(2);
const spec = JSON.parse(fs.readFileSync(specPath, 'utf8'));
const FPS = spec.fps || 30;

function findChromium() {
  const cands = [process.env.CHROMIUM_PATH, ...fs.readdirSync('/opt/pw-browsers').filter(d => d.startsWith('chromium_headless_shell')).map(d => '/opt/pw-browsers/' + d)].filter(Boolean);
  for (const c of cands) {
    if (!fs.existsSync(c)) continue;
    if (fs.statSync(c).isFile()) return c;
    // search inside a browsers dir
    const stack = [c];
    while (stack.length) {
      const d = stack.pop();
      for (const f of fs.readdirSync(d, { withFileTypes: true })) {
        const p = path.join(d, f.name);
        if (f.isDirectory()) stack.push(p);
        else if (/^(headless_shell|chrome-headless-shell)$/.test(f.name)) return p;
      }
    }
  }
  return undefined;
}

const browser = await chromium.launch({ executablePath: findChromium() });
const page = await browser.newPage({ viewport: { width: 1080, height: 1920 }, deviceScaleFactor: 1 });
await page.addInitScript(s => { window.__SPEC__ = s; }, spec);
await page.goto('file://' + path.join(dir, 'story.html'));
await page.evaluate(() => { window.renderAt(0); return document.fonts.ready; });
await page.waitForTimeout(300);
const total = await page.evaluate(() => window.TOTAL);

if (flag === '--preview') {
  const ts = list.split(',').map(Number);
  for (const t of ts) {
    await page.evaluate(t => window.renderAt(t), t);
    await page.screenshot({ path: `${out}-${t}.png` });
  }
  console.log('preview done', ts.length, 'frames, total', total);
} else {
  const ff = spawn('ffmpeg', ['-y', '-loglevel', 'error', '-f', 'image2pipe', '-framerate', String(FPS), '-c:v', 'mjpeg', '-i', '-',
    '-f', 'lavfi', '-i', 'anullsrc=r=44100:cl=stereo', '-shortest',
    '-c:v', 'libx264', '-preset', 'medium', '-crf', '19', '-pix_fmt', 'yuv420p', '-r', String(FPS),
    '-c:a', 'aac', '-b:a', '128k', '-movflags', '+faststart', out], { stdio: ['pipe', 'inherit', 'inherit'] });
  const n = Math.round(total * FPS);
  for (let i = 0; i < n; i++) {
    await page.evaluate(t => window.renderAt(t), i / FPS);
    const buf = await page.screenshot({ type: 'jpeg', quality: 93 });
    if (!ff.stdin.write(buf)) await new Promise(r => ff.stdin.once('drain', r));
    if (i === Math.round(1.4 * FPS)) fs.writeFileSync(out.replace(/\.mp4$/, '') + '_cover.jpg', buf);
  }
  ff.stdin.end();
  await new Promise(r => ff.on('close', r));
  console.log(`rendered ${out} (${total.toFixed(1)}s, ${n} frames)`);
}
await browser.close();
