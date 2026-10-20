#!/usr/bin/env python3
"""
Audio for story reels — NO music. Original, procedurally synthesised sound effects
(typing, clicks, pops, whooshes, dings, stamps) synced to the animations in story.html,
plus an optional voiceover.

Two commands:

1) Fit a voiceover to the spec (run BEFORE rendering the video):
   python3 audio.py fitvo spec.json vo.mp3 spec.timed.json vo_aligned.wav
   - Scenes that should be spoken carry a "vo" text field; the vo.mp3 must speak those
     lines in order with a short pause between them (generate them as one take,
     one line per paragraph).
   - Splits the take at its longest pauses, stretches each scene's "dur" so its line fits
     (+ breathing room), and writes the aligned voice track.

2) Mix SFX (+ aligned voice) onto the rendered silent video:
   python3 audio.py mix spec.timed.json silent.mp4 out.mp4 [vo_aligned.wav]
"""
import json, re, subprocess, sys
import numpy as np
from scipy.io import wavfile

SR = 44100
rng = np.random.default_rng(7)

# ---------------- synthesis (all original, no samples) ----------------
def env(n, a=0.002, d=0.05):
    t = np.arange(n) / SR
    e = np.minimum(1, t / max(a, 1e-4)) * np.exp(-t / max(d, 1e-4))
    return e

def key_click():
    n = int(SR * 0.045)
    x = rng.standard_normal(n)
    x = np.diff(np.concatenate([[0], x]))            # brighten (high-pass-ish)
    body = np.sin(2 * np.pi * rng.uniform(1700, 2600) * np.arange(n) / SR) * 0.35
    return (x * 0.55 + body) * env(n, 0.0008, 0.010) * rng.uniform(0.7, 1.0)

def mouse_click():
    a = key_click() * 0.9
    n = int(SR * 0.07); out = np.zeros(n)
    out[:len(a)] += a
    b = key_click() * 0.6; s = int(SR * 0.022)
    out[s:s + len(b)] += b[:n - s]
    return out

def pop(f0=720, f1=330, dur=0.09, g=0.7):
    n = int(SR * dur); t = np.arange(n) / SR
    f = np.linspace(f0, f1, n)
    ph = 2 * np.pi * np.cumsum(f) / SR
    return np.sin(ph) * env(n, 0.002, dur / 3.2) * g

def tick():
    return pop(1900, 1500, 0.035, 0.35)

def bubble():
    return pop(520, 900, 0.11, 0.55)                  # upward "message" blip

def ding():
    n = int(SR * 0.6); t = np.arange(n) / SR
    x = np.sin(2 * np.pi * 1318.5 * t) + 0.6 * np.sin(2 * np.pi * 1975.5 * t) + 0.25 * np.sin(2 * np.pi * 2637 * t)
    return x * env(n, 0.003, 0.18) * 0.28

def thud():
    n = int(SR * 0.25); t = np.arange(n) / SR
    low = np.sin(2 * np.pi * np.linspace(140, 55, n) * t) * env(n, 0.002, 0.07)
    c = key_click(); c = np.pad(c, (0, max(0, n - len(c))))[:n]
    return low * 0.9 + c * 0.6

def whoosh(dur=0.45, g=0.45):
    n = int(SR * dur)
    x = rng.standard_normal(n)
    # sweep a simple one-pole low-pass cutoff up then down
    t = np.linspace(0, 1, n)
    a = 0.02 + 0.5 * np.sin(np.pi * t) ** 2
    y = np.zeros(n); acc = 0.0
    for i in range(n):
        acc += a[i] * (x[i] - acc); y[i] = acc
    y = y - np.convolve(y, np.ones(40) / 40, mode='same') * 0.6
    shape = np.sin(np.pi * t) ** 1.5
    return y / (np.abs(y).max() + 1e-9) * shape * g

SFX = {'key': key_click, 'click': mouse_click, 'pop': pop, 'tick': tick, 'bubble': bubble,
       'ding': ding, 'thud': thud, 'whoosh': whoosh, 'swish': lambda: whoosh(0.3, 0.22)}
GAIN = {'key': 0.55, 'click': 0.9, 'pop': 0.55, 'tick': 0.5, 'bubble': 0.6, 'ding': 0.7,
        'thud': 0.9, 'whoosh': 0.55, 'swish': 0.5}

# ---------------- event extraction (mirrors story.html timings) ----------------
def words_in(tx, cls):
    if (cls or '').startswith('accent'):
        return [tx]
    return [w for w in re.split(r'(?<= )', tx) if w]

def scene_events(sc, t0, idx):
    ev = []
    add = lambda t, k: ev.append((t0 + t, k))
    if idx > 0:
        add(-0.18, 'whoosh')
    start = sc.get('textAt', 0); gap = sc.get('gap', .26); k = 0
    for i, ln in enumerate(sc.get('lines', [])):
        for tx, cls in ln:
            for w in words_in(tx, cls):
                s = start + i * gap + k * .05; k += 1
                if (cls or '').startswith('accent'):
                    add(s + .05, 'pop')
    v = sc.get('visual')
    if v:
        add(.2, 'swish'); ty = v['type']
        if ty == 'browser':
            for c in range(len(v.get('url', ''))): add(.5 + c / 18, 'key')
            for i, _ in enumerate(v.get('bubbles', [])): add(v.get('bubbleAt', 2.4) + i * .3, 'pop')
            if v.get('thought'): add(v.get('thoughtAt', 3), 'bubble')
        elif ty == 'search':
            for c in range(len(v.get('query', ''))): add(.5 + c / 16, 'key')
            add(.5 + len(v.get('query', '')) / 16 + .05, 'click')
            for i, _ in enumerate(v.get('results', [])): add(v.get('resultsAt', 1.8) + i * .35, 'tick')
        elif ty == 'chat':
            for i, m in enumerate(v.get('messages', [])):
                add(m.get('at', .6 + i * .9), 'tick' if m.get('divider') else 'bubble')
            if v.get('stamp'): add(v.get('stampAt', 2.6) + .12, 'thud')
        elif ty == 'tabs':
            add(1.2, 'click'); add(v.get('toastAt', 2.6), 'ding')
        elif ty == 'calc':
            n = len(v.get('rows', []))
            for i in range(n): add(.6 + i * .5, 'tick')
            add(.6 + n * .5 + .2, 'ding')
        elif ty == 'list':
            at, st = v.get('at', .9), v.get('step', 1.6)
            for i, _ in enumerate(v.get('items', [])): add(at + i * st, 'pop'); add(at + i * st + .4, 'tick')
        elif ty == 'comment':
            kw = v.get('keyword', '')
            for c in range(len(kw)): add(.8 + c / 6, 'key')
            add(v.get('sendAt', 2.6) - .05, 'click'); add(v.get('sendAt', 2.6) + .1, 'bubble')
        elif ty == 'versus':
            nl = len(v['left']['items'])
            add(.4, 'pop')
            for i in range(nl): add(.75 + i * .35, 'tick')
            b2 = .4 + nl * .35 + .3; add(b2, 'pop')
            for i in range(len(v['right']['items'])): add(b2 + .35 + i * .35, 'tick')
        elif ty == 'profile':
            for i in range(6): add(.9 + i * .12, 'tick')
    for s in sc.get('stickers', []): add(s.get('at', 1), 'pop')
    for p in sc.get('pills', []): add(p.get('at', 1), 'bubble')
    if sc.get('shakeAt') is not None: add(sc['shakeAt'], 'thud')
    if sc.get('brand'): add(sc.get('brandAt', 3.6), 'ding')
    # keep only events inside the scene
    return [(t, k) for t, k in ev if t0 - .3 <= t < t0 + sc['dur']]

def all_events(spec):
    ev, t0 = [], 0.0
    for i, sc in enumerate(spec['scenes']):
        ev += scene_events(sc, t0, i); t0 += sc['dur']
    return ev, t0

# ---------------- helpers ----------------
def load_audio(path):
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', path, '-f', 'f32le', '-ac', '1', '-ar', str(SR), '-'],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, dtype=np.float32).astype(np.float64)

def find_pauses(x, min_len=0.22):
    frame = int(SR * 0.02)
    n = len(x) // frame
    rms = np.sqrt(np.mean(x[:n * frame].reshape(n, frame) ** 2, axis=1) + 1e-12)
    thr = max(np.percentile(rms, 20) * 1.8, rms.max() * 0.02)
    quiet = rms < thr
    pauses, i = [], 0
    while i < n:
        if quiet[i]:
            j = i
            while j < n and quiet[j]: j += 1
            if (j - i) * 0.02 >= min_len: pauses.append(((i * 0.02), (j * 0.02)))
            i = j
        else:
            i += 1
    return pauses

def fitvo(spec_path, vo_path, out_spec, out_wav):
    spec = json.load(open(spec_path))
    x = load_audio(vo_path)
    total = len(x) / SR
    spoken = [i for i, sc in enumerate(spec['scenes']) if sc.get('vo')]
    need = len(spoken) - 1
    pauses = [p for p in find_pauses(x) if 0.3 < p[0] < total - 0.3]
    pauses = sorted(sorted(pauses, key=lambda p: p[1] - p[0], reverse=True)[:need])
    cuts = [0.0] + [(a + b) / 2 for a, b in pauses] + [total]
    if len(cuts) - 1 != len(spoken):
        # fall back: split by text length
        lens = np.array([len(spec['scenes'][i]['vo']) for i in spoken], float)
        cuts = list(np.concatenate([[0], np.cumsum(lens / lens.sum() * total)]))
    segs = [x[int(cuts[k] * SR):int(cuts[k + 1] * SR)] for k in range(len(spoken))]
    lead = 0.25
    t0, track = 0.0, []
    seg_iter = iter(segs)
    for i, sc in enumerate(spec['scenes']):
        if sc.get('vo'):
            s = next(seg_iter)
            # trim silence at edges
            nz = np.where(np.abs(s) > np.abs(s).max() * 0.02)[0]
            if len(nz): s = s[max(0, nz[0] - int(.03 * SR)):nz[-1] + int(.08 * SR)]
            sc['dur'] = round(max(sc.get('minDur', 2.2), lead + len(s) / SR + 0.45), 2)
            track.append((t0 + lead, s))
        t0 += sc['dur']
    out = np.zeros(int((t0 + 0.5) * SR))
    for st, s in track:
        a = int(st * SR); out[a:a + len(s)] += s[:len(out) - a]
    json.dump(spec, open(out_spec, 'w'), ensure_ascii=False, indent=1)
    wavfile.write(out_wav, SR, (np.clip(out, -1, 1) * 32767).astype(np.int16))
    print(f'fitted {len(spoken)} lines, total {t0:.1f}s')

def mix(spec_path, video, out, vo_wav=None):
    spec = json.load(open(spec_path))
    ev, total = all_events(spec)
    L = int((total + 0.6) * SR)
    sfx = np.zeros(L)
    for t, k in ev:
        s = SFX[k]() * GAIN[k]
        a = int(max(0, t) * SR); b = min(L, a + len(s))
        sfx[a:b] += s[:b - a]
    out_a = sfx * 0.55
    if vo_wav:
        sr, v = wavfile.read(vo_wav); v = v.astype(np.float64) / 32768
        if v.ndim > 1: v = v.mean(axis=1)
        v = np.pad(v, (0, max(0, L - len(v))))[:L]
        # duck sfx under the voice
        envv = np.convolve(np.abs(v), np.ones(int(.15 * SR)) / int(.15 * SR), mode='same')
        duck = 1 - 0.55 * np.clip(envv / (envv.max() + 1e-9) * 4, 0, 1)
        out_a = sfx * 0.45 * duck + v * 1.0
    peak = np.abs(out_a).max()
    if peak > 0.95: out_a = out_a / peak * 0.95
    wav = out.rsplit('.', 1)[0] + '_audio.wav'
    wavfile.write(wav, SR, (out_a * 32767).astype(np.int16))
    subprocess.run(['ffmpeg', '-y', '-v', 'error', '-i', video, '-i', wav, '-map', '0:v', '-map', '1:a',
                    '-c:v', 'copy', '-c:a', 'aac', '-b:a', '160k', '-shortest', '-movflags', '+faststart', out], check=True)
    print(f'mixed {len(ev)} sound events -> {out}')

if __name__ == '__main__':
    cmd = sys.argv[1]
    if cmd == 'fitvo': fitvo(*sys.argv[2:6])
    elif cmd == 'mix': mix(*sys.argv[2:5], sys.argv[5] if len(sys.argv) > 5 else None)
