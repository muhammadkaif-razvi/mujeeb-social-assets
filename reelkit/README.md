# Story reel template v4 (script on screen + typing/click sound effects, NO music)

Text-led story reels: story text where every word pops in, highlighter swipes behind accent words, camera punch-in + slow drift, optional screen shake on the pain moment, diagonal swipe transitions, animated colour blobs, phone-frame mockups, emoji stickers, "Save / Share" pills, story-style progress bar. 1080x1920 MP4, ~45–60 s. Sound = procedural sound effects from audio.py (keyboard typing, mouse clicks, pops, whooshes, dings) — NEVER music, and never tell Raza to add trending audio. Optional AI voiceover (see Voice).
Themes: "global" (Mujeeb Technologies — blue/cyan, English, SaaS founders, logo.png = LOGO.png) and "local" (BARKATI — Deep Navy #0A1A3F + Electric Cyan #00C2FF, Hinglish; see claude/local-brand.md).

## Setup (fresh container)
1. project_read claude/story-reel/story.html, claude/story-reel/render.mjs, claude/story-reel/audio.py and the example-*.json files into one directory (pip install numpy if missing; ffmpeg is needed).
2. In that directory: `npm init -y && npm i @fontsource/playfair-display@5.1.0 @fontsource/inter@5.1.0 playwright-core@1.48.2`
3. Copy fonts next to story.html: `cp node_modules/@fontsource/playfair-display/files/playfair-display-latin-{400,700,900}-{italic,normal}.woff2 node_modules/@fontsource/inter/files/inter-latin-{400,500,600,700,800,900}-normal.woff2 .`
4. Logo:
   - global (Mujeeb Technologies): project_read LOGO.png, make near-white pixels transparent, crop to bbox, resize to 256px wide, save as `logo.png` next to story.html; final scene "brand": true (brandSub defaults to mujeebtechnologies.com).
   - local (BARKATI): render claude/barkati/barkati-logo-horizontal.svg to PNG with the headless shell at 2x, crop to the alpha bbox, save as `barkati-logo-tight.png`; final scene "brand": true, "brandWide": true, "brandLogo": "barkati-logo-tight.png", "brandH": 64.
   Emoji use the system "Noto Color Emoji" font (check `fc-list | grep -i emoji`; if missing, `apt-get install -y fonts-noto-color-emoji` or drop the emoji).
5. Render: `node render.mjs spec.json silent.mp4` then `python3 audio.py mix spec.json silent.mp4 out.mp4` (adds the sound effects; the final file is out.mp4) (≈5 min for 50 s; also writes out_cover.jpg). One render per shell command, in the background if needed, so a 10-minute command timeout isn't hit. Preview stills: `node render.mjs spec.json pv/p --preview 2.5,8,12` → pv/p-2.5.png… render.mjs finds /opt/pw-browsers/chromium_headless_shell-* automatically (the plain chromium binary fails: old headless removed).

## Spec format
`{"theme":"global"|"local","style":"editorial"|"dark"|"bold","layout":"stack"|"flip"|"center"|"poster","transition":"swipe"|"slide"|"zoom","scenes":[{dur, bg:"light"|"blue", lines, top?, visual?, visTop?, stickers?, pills?, shakeAt?, brand?, brandWide?, brandLogo?, brandH?, brandAt?, brandName?, brandSub?}]}`
- Per scene you may also set "layout" (overrides the top-level one), "vo" (voiceover line), "textBottom" (flip, default 280), "flipVisTop" (flip, default 170).
- lines: array of lines; each line is array of [text, style]; style "" | "accent" or "accent-ul" (huge bold + highlighter swipe; keep to 1–2 words) | "big" (bold) | "soft". Emoji allowed in text.
- stickers: [{emoji, x, y, size, at, rot}] — pop-in emoji with wobble, in empty space (x≈850–880 beside text, or y≈560–620 between text and mockup).
- pills: [{text, y, at, x?, rot?, hot?}] — audience tag on scene 1 at y 140 (hot, at 0), "📌 Save…" on the list scene at y≈1640, share prompt on a blue scene at y≈1250.
- shakeAt: seconds into the scene to shake the camera (stamp / confusion moment).
- visual types:
  - profile {handle, bio, initial} (phone frame, Instagram-style)
  - search {query, resultsAt, results[{title, sub, dim?}]} (phone frame, Google-style)
  - chat {name, status, initial, stamp, stampAt, minH, messages[{text, me?, meta?, at?} | {divider, at}]} (phone frame, red stamp)
  - browser {url, headline, sub, buttons[], bubbles[[x,y,size]], bubbleAt, thought, thoughtAt}
  - tabs {tabs[2], oldHeadline, chip, headline, sub, button, toast, toastAt}
  - calc {title, chip, rows[], icons[], resultLabel, result} ← words only, never invented figures
  - list {items[[title, sub]], at, step} (numbers turn into green ticks)
  - versus {left:{title, items[]}, right:{title, items[]}, leftIcon?, rightIcon?} (two cards; left rows struck through; rows ≤ 6 words; visTop ≈ 720–760)
  - comment {keyword, sendAt, noteAt, note(lines)}
  - chart {title, chip, up, flat}
- visTop: ~720–880 depending on how many text lines sit above it. ALWAYS preview stills of every scene and fix overlaps before the full render.

## Variety — so reels don't all look the same (REQUIRED for batches)
### Visual styles (top-level "style")
- "editorial" (default): light canvas, Playfair italic story text, highlighter swipes.
- "dark": full navy canvas, white text, cyan accent words; transition screens turn cyan with navy text.
- "bold": white poster canvas, heavy upright Inter Black text, accent words in solid cyan blocks.
Daily BARKATI batch of 3: one editorial, one dark, one bold (rotate which comes first day to day). Weekly single reels: rotate week to week (check the content log).
### Story formats — 3 different formats per daily batch of 3
1. Problem story: belief hook → reversal → scenario → pain → competitor wins → do the maths / hisaab → 3-point fix → CTA.
2. Myth vs Fact: myths hook → versus (MYTH / FACT) → blue one-liner → CTA.
3. Before vs After: versus (PEHLE/BAAD or BEFORE/AFTER, icons 😩 / 😍) → browser/tabs mockup of the "after" page → CTA.
4. POV chat: most of the reel is one customer conversation in the chat mockup, then the stamp → short text scenes → CTA.
5. "3 mistakes" countdown: "Mistake #3 / #2 / #1" scenes each with an accent word + small mockup → "the right way" list → CTA.
6. Quiz / checklist: "Does your business have these 4 things?" → list → "If even one is ❌…" blue scene → CTA.
Also vary: number of scenes (7–11), mockups used, sticker emoji, pill wording, CTA keyword.

### Layouts (top-level "layout", or per scene) — REQUIRED to vary
- "stack" (default): text on top, mockup below.
- "flip": mockup at the top (auto-centred in the free space), text anchored at the bottom. Pills on mockup scenes go at y≈1030 (between mockup and text) — not at 140/1640.
- "center": text centred horizontally, mockup below.
- "poster": oversized text, mockup tilted and pushed right as a "card on a poster".
### Transitions (top-level "transition")
- "swipe" (default): diagonal colour band. "slide": next scene slides up like a story card while the old one darkens. "zoom": radial colour flash.
### Combining for a batch
Every reel in a batch gets a DIFFERENT style + layout + transition combination (e.g. bold/flip/slide, dark/center/zoom, editorial/poster/swipe). Within one reel you can switch layout on 1–2 scenes for rhythm.

## Sound (audio.py) — NO MUSIC, EVER
- `python3 audio.py mix spec.json silent.mp4 out.mp4 [vo_aligned.wav]` builds a sound-effect track that follows the scene timings: whoosh on every cut, keyboard typing while search/URL/comment text types, mouse click on taps/send, bubble pop per chat message, thud on stamps & shakes, tick per list/calc row, ding on toasts/brand. All synthesised (no samples, no licences). Peak-limited, AAC.
- Never add music or suggest "trending audio". If a caption reminder is needed: "sound already added — post as is".
- Listen-check: extract 3 short clips (ffmpeg -ss) and confirm the track is not silent: `ffmpeg -i out.mp4 -af volumedetect -f null -` (mean_volume should be above -40 dB).

## Voice (optional, ElevenLabs)
- Give each scene a "vo" line (Hinglish / English, ~2.3 words per second of the scene).
- Generate ONE take of the whole script with the ElevenLabs connector (creative_generate_speech, model eleven_multilingual_v2, generations_count 1), download the mp3; if the download URL is blocked by the network, skip voice and ship the SFX version.
- `python3 audio.py fitvo spec.json vo.mp3 spec.timed.json vo_aligned.wav` stretches scene durations to the voice; then render spec.timed.json and `mix` with vo_aligned.wav (SFX are ducked under the voice).

## Engagement rules (every reel)
- First 1.5 s: a scroll-stopper — a specific situation the viewer recognises ("Raat 11 baje DM aaya: 'bridal package ka rate?'"), never a generic "Do you have a business?".
- Open a loop early ("…aur subah tak woh customer kahin aur book kar chuka tha") and close it before the CTA.
- One concrete payoff the viewer can use today (a 3-point checklist, a question to ask, what to compare).
- Something moves every 1–2 s (word pops, mockup action, sticker, shake). Max ~12 words on screen per scene.
- End with ONE comment-keyword CTA and a save/share pill earlier.

## Rules
- Honest copy only: no invented stats, clients, results, prices or turnaround promises. Mockup businesses must be generic placeholders, never a real company.
- Don't name the tech stack.
- Local (BARKATI) reels never show Mujeeb Technologies; global reels never show BARKATI.
