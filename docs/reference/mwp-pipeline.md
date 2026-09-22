# The My Weird Prompts pipeline — where this plugs in

Verified 2026-09-22 by reading the repo. The consumer of everything in this project
is the *My Weird Prompts* podcast pipeline.

Repo: `~/repos/github/mwp-podcast/My-Weird-Prompts` →
`github.com/danielrosehill/My-Weird-Prompts`. The repo states elsewhere that the
production system is private; treat it as private.

## Current TTS path

**Engine: regular English Chatterbox.** `chatterbox-tts>=0.1.6`, pinned at
`modal_app/app_config.py:75`. Import is `from chatterbox.tts import ChatterboxTTS`
— **not** `ChatterboxMultilingualTTS`. `pipeline/tts/chatterbox.py:23` explains the
choice: regular Chatterbox hallucinates less with voice clones than Turbo.

**`language_id` does not appear anywhere in the repo.** It cannot — the English
class has no such parameter.

Two generation paths:

| Path | File | Call site |
| --- | --- | --- |
| Production (Modal GPU, or RunPod serverless fallback) | `modal_app/stages/tts_parallel.py` | `tts_worker()` line 41; `wav = model.generate(text)` at line 88 |
| Non-parallel | `pipeline/tts/chatterbox.py` | `generate_dialogue_audio()`; `wav = model.generate(text)` at line 355 |

Both dialogue call sites are **bare** — no `exaggeration`, `cfg_weight` or
`temperature`. Voice identity comes entirely from pre-computed `Conditionals`
(`*_conds.pt`) loaded from a Modal volume or R2. Voices: corn, herman, raz, dorothy,
tim, jacob, mindy, bernard, plus daniel and hilbert.

Sampler parameters appear only on **show elements**, not dialogue —
`modal_app/generate_show_elements.py:134` uses `exaggeration=0.3, cfg_weight=0.5,
temperature=0.6`.

## The segmentation that already exists

This is the most important structural fact for this project: **the pipeline already
splits turns into multiple clips and concatenates them.**

- `MAX_CHARS_PER_TTS = 250` — `modal_app/stages/tts_parallel.py:191`, mirrored as
  `MAX_CHARS_PER_TTS_REQUEST = 250` in `pipeline/config/constants.py:211`.
- Concatenation, `tts_parallel.py:421-430`:

```python
dialogue_path = episode_dir / "dialogue.mp3"
concat_file = segments_dir / "concat.txt"
...
["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(concat_file),
 "-codec:a", "libmp3lame", "-b:a", "192k", str(dialogue_path)]
```

(The non-parallel path writes per-segment `.m4a` at 96k AAC and concats to
`dialogue.m4a`.) Final assembly — room tone, EQ, fades, LUFS/true-peak
normalisation, Podcasting 2.0 chapters — is `pipeline/audio/assembly.py`,
`concatenate_episode()` line 247.

**Consequence:** the voice note treats per-turn multi-clip generation as a new
"additional challenge". It is not new. A 250-character chunker and an ffmpeg concat
already exist; the change is to make the split points *language-driven as well as
length-driven*, and to carry a `language_id` per chunk. That is a meaningfully
smaller change than the note assumes.

## The plug point for pronunciation

`pipeline/audio/tts_pronunciation.py` (191 lines) is the only text-normalisation
layer, invoked via `normalize_text()` from `tts_parallel.py:195` and `:545`.

```python
PRONUNCIATION_OVERRIDES: dict[str, str] = {}   # line 48
# "Empty by default — do not add speculative entries."
```

It is a **whole-token, case-insensitive string substitution** — no phonemes, no IPA,
no G2P. It is empty. It sits exactly where a Hebrew respelling dictionary would go.

There is **no** Hebrew-aware, transliteration-aware or language-tagging logic
anywhere in `pipeline/` or `modal_app/`.

### A warning written into that file

The docstring (lines 4-16) records that acronym phonetic spell-out was **removed on
2026-06-09**: spelling out letter names made Chatterbox read "URL" as the sentence
"you are el". ALLCAPS now passes through untouched.

Read that as a result, not an anecdote — **naive respelling of a word into
pseudo-phonetic English has already failed once in this exact pipeline.** Any
"just respell *challah* as *KHA-lah*" baseline inherits that risk.

The live work in the file is an English contraction pass ("it is" → "it's"), added
2026-07-20, kill-switchable with `TTS_CONTRACTIONS=0`. That is the precedent for
how a new normalisation stage gets shipped here: behind an env kill switch.

### Upstream, pronunciation is already being deferred to this layer

Script-generation prompts push pronunciation responsibility downstream to a layer
that does not handle it: `pipeline/config/prompts.py:293`, `:1049`;
`pipeline/config/diy_prompts.py:152`; `system-prompts/*.md`.
`bluffers_guide_prompts.py:96` asks the model to inline-respell loanwords
("'terroir' — pronounced tare-WAHR") and `prompts.py:1142-1199` has a research-time
`pronunciation_guide` field using simple phonetics. **Nothing wires either into
TTS.** So there is already an unconsumed pronunciation signal in the pipeline.

## The cheap baseline this implies

Before building any model: populate `PRONUNCIATION_OVERRIDES` with respellings for
the ~40 Hebrew terms that actually occur in the corpus, and measure. It is an
afternoon's work, it needs no model, and it gives the real numbers against which the
model chain has to justify itself. See `docs/spec.md` for why it is not the answer,
only the baseline.
