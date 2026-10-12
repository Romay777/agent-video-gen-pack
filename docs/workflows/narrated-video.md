# Workflow: narrated video (script → AI voice-over → Remotion)

From "make me a video about X" to a narrated Remotion video, here with subtitles.

> This is one worked example of a route through the toolkit. Your task may need fewer steps, other steps or a different order: subtitles, titles and effects in particular are there only if the video calls for them.

```
brief → script (scenes) → TTS per scene → timings per scene → Remotion composition → Studio preview → render (on request)
```

## Writing the script

- Clarify only what you can't infer: topic, audience, length, language, aspect ratio (default 1920×1080; 1080×1920 for Shorts/Reels/TikTok), tone. Otherwise pick sensible defaults and state them.
- Narration is **spoken**: short sentences, no parentheses, no symbols the voice can't read. Spell out numbers, units and acronyms the way they should be pronounced.
- Pace: ~150 spoken words per minute. 30 s ≈ 75 words; 60 s ≈ 150 words. Each scene also adds 0.6 s of pause. After generating, add up the real `duration` values and trim or extend the text to hit the requested length.
- This example splits the narration into scenes, one idea each. It names scenes `scene-01`, `scene-02`, … and keeps the narration in `work/<video>/scene-NN.txt` so a line can be re-taken without touching the others.
- Show the script to the person before spending credits when the video is long (more than ~2 minutes) or the brief was vague. For short videos just proceed.

## Generating audio and timings

Create the Remotion project first ([../remotion-setup.md](../remotion-setup.md)): the audio goes into its `public/`, and `create-video` should be the one to create that folder.

```bash
V=my-video/public/voiceover          # inside the Remotion project
for f in work/demo/scene-*.txt; do
  id=$(basename "$f" .txt)
  uv run scripts/tts.py --file "$f" -o "$V/$id.mp3"
  uv run scripts/transcribe.py "$V/$id.mp3" -o "$V/$id.json"
done
```

Then read each JSON: `text` vs the script (mispronunciation shows up as a different word and low `confidence`), `duration`, and `words`. If a take is bad, change the wording (or `--voice`) and redo only that scene.

## Building the composition

Follow the `remotion-best-practices` skill for structure, fonts, animation and layout; what each scene shows is yours to design with it (shapes, text, charts, images the person supplies). How this example connects the pieces:

1. **Duration comes from the audio.** Each timings JSON has `duration` (seconds). Scene length = `ceil((duration + pad) * fps)`. Use `calculateMetadata` to set total `durationInFrames` so changing a take changes the video length automatically.
2. **Each scene lives in its own `<Series.Sequence>`** with its `<Audio src={staticFile("voiceover/scene-01.mp3")} />`. Time inside the sequence starts at 0, which matches the timings JSON, so nothing needs to be offset.
3. **Subtitles**, if the video has them – put `captions` from the JSON into `<BasicCaptions>` (element described in the skill's `remotion-captions/display-captions.md`; copy its source from https://www.remotion.dev/elements/captions/basic-captions.md into `src/basic-captions.tsx`). Needs `npx remotion add @remotion/captions @remotion/media`.
4. **Sync visuals to words.** Convert seconds to frames with `Math.round(word.start * fps)` and use that as the `from` of a `<Sequence>` or as the input range of `interpolate()` / `spring()`. Examples: show a bullet when its keyword is spoken; highlight the current word; cut to the next shot on a sentence end (`sentences[i].end`).
5. **Delay start slightly** (`from={Math.round(0.2 * fps)}` on `<Audio>`) if visuals need a beat before the voice begins.

A complete, type-checked reference lives in [`examples/`](../examples/):

- [`examples/Narrated.tsx`](../examples/Narrated.tsx) – multi-scene composition: audio per scene, `calculateMetadata`, captions.
- [`examples/Root.tsx`](../examples/Root.tsx) – registers the composition and loads the per-scene JSON as default props.

It expects `public/voiceover/scene-01.{mp3,json}`, `scene-02.{mp3,json}` and `src/basic-captions.tsx`. It was type-checked and rendered against the stock `create-video --blank` template (Remotion 4.0.535); JSON imports work with that template's `tsconfig.json` unchanged.

Per the skill's captions guide, when the person wants to edit captions in Studio, inline the `captions` array literal in the `<BasicCaptions captions={[...]}>` prop instead of passing a variable.

## Preview, then render

```bash
cd my-video && npx remotion studio            # let the person look first
npx remotion render Narrated out/narrated.mp4 # only when asked
```

Check before handing over:

- `npx tsc` (or `npm run lint`) passes.
- A still around the first spoken words shows what you intended (here, the right caption): `npx remotion still Narrated out/check.png --frame=45`.
- Total length ≈ sum of scene durations + padding.
- Audio is present in the render: `ffprobe -v error -show_entries stream=codec_type -of csv=p=0 out/narrated.mp4` lists `video` and `audio`.

## Troubleshooting

| Symptom | Cause / fix |
| --- | --- |
| `OPENROUTER_API_KEY is not set` | Add it to `.env` or export it. Ask the person for it; don't invent one. |
| HTTP 401/402/403/404/429/502 from `tts.py` | See the table in [openrouter-tts.md](../openrouter-tts.md#errors). |
| `transcribe.py` first run is slow | It is downloading ~2.4 GB into `.cache/models/`. Run `scripts/download_model.py` ahead of time. |
| `External data path escapes model directory` | Model was loaded from the HuggingFace cache; use `scripts/asr_models.py` (stores real files in `.cache/models/`). |
| Words missing or wrong in the timings | Mispronounced or unusual word: rephrase in the script and re-take that scene. |
| `remotion still/render` fails with `Z_DATA_ERROR` on the first run | The headless browser download was interrupted; run the command again. |
| Subtitles drift in a scene | The audio file used in `<Audio>` isn't the one that was transcribed (re-take without re-transcribing). Re-run `transcribe.py`. |
