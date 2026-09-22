# Chatterbox TTS — reference for the Hebrew code-switching problem

Verified 2026-09-22 by reading the source at
<https://github.com/resemble-ai/chatterbox> (`master`), not only the README.
Licence: **MIT**, Copyright (c) 2025 Resemble AI.

## The headline finding

**Chatterbox has no inline language tags.** `language_id` is a *whole-call*
parameter, not a marker you embed in the text. There is no `<he>…</he>`,
no SSML `xml:lang`, no per-span switch of any kind. The README's only inline
markers are paralinguistic (`[cough]`, `[laugh]`, `[chuckle]`) and they exist
only on the Turbo/Nano classes.

Consequence for this project: **a sentence containing a Hebrew word cannot be
synthesised in one call.** It must be split into segments, each generated with
its own `language_id`, and the segments concatenated. The per-turn multi-clip
assembly is therefore mandatory, not an optimisation.

## Classes

| Class | Import | Languages |
| --- | --- | --- |
| `ChatterboxTTS` | `from chatterbox.tts import ChatterboxTTS` | English only — **this is what MWP currently uses** |
| `ChatterboxMultilingualTTS` | `from chatterbox.mtl_tts import ChatterboxMultilingualTTS` | 23, including Hebrew |
| `ChatterboxTurboTTS` | `from chatterbox.tts_turbo import ChatterboxTurboTTS` | Turbo; `nano=True` for Nano |

Moving to Hebrew segments means moving the pipeline to
`ChatterboxMultilingualTTS`. That is a model swap, not a flag.

## Loading

```python
from chatterbox.mtl_tts import ChatterboxMultilingualTTS
model = ChatterboxMultilingualTTS.from_pretrained(device="cuda", t3_model="v3")
```

`t3_model` may be omitted or set to `"v2"` for the older checkpoint. Weights come
from the HF repo `ResembleAI/chatterbox`.

## `generate()` — full signature

From `src/chatterbox/mtl_tts.py`, confirmed by reading the file:

```python
def generate(
    self,
    text,
    language_id,                 # required, positional — 2nd argument
    audio_prompt_path=None,
    exaggeration=0.5,
    cfg_weight=0.5,
    temperature=0.8,
    repetition_penalty=1.2,
    min_p=0.05,
    top_p=1.0,
):
```

The README documents none of `temperature`, `repetition_penalty`, `min_p` or
`top_p`, and shows `exaggeration` / `cfg_weight` only in prose. The defaults above
are read from source and are authoritative.

Validation: an unrecognised `language_id` raises `ValueError` listing the supported
set. It is lowercased before use.

Text handling: `punc_norm(text)` runs first, then
`self.tokenizer.text_to_tokens(text, language_id=...)`. **The tokenizer is
language-conditioned**, which is the mechanism reason a single call cannot serve
two scripts — one call, one language token path.

## Supported `language_id` values (23)

`ar` `da` `de` `el` **`he`** `en` `es` `fi` `fr` `hi` `it` `ja` `ko` `ms` `nl`
`no` `pl` `pt` `ru` `sv` `sw` `tr` `zh`

**Hebrew is supported** in Multilingual V3 (`"he": "Hebrew"` in
`SUPPORTED_LANGUAGES`). This is what makes the whole plan viable — stage 2 has a
consumer.

Not verified: how good `he` actually sounds, or whether it expects Hebrew script
(it almost certainly does, given the language-conditioned tokenizer) versus
pointed/vocalised Hebrew. **Test before building anything on top of it.**

## Audio

- Sample rate: `model.sr` = `S3GEN_SR` = **24000 Hz** (`models/s3gen/const.py`).
- Save with `torchaudio.save(path, wav, model.sr)`.
- Reference voice clip: ~10 s (`audio_prompt_path`).
- Every output carries an imperceptible **Perth neural watermark**, readable via
  `perth.PerthImplicitWatermarker().get_watermark(audio, sample_rate=sr)` → 0.0 or 1.0.

## Two tips that bear directly on cross-language segments

From the README's prose, not the API:

- **`cfg_weight=0` reduces accent bleed on cross-language transfer.** Directly
  relevant: our English reference voice will be driving Hebrew segments.
- `language_id` "should match the reference clip's language". We will be violating
  this deliberately — one English speaker voice across both segment languages —
  so expect accent artefacts on the Hebrew and treat `cfg_weight` as the knob.

`generate()` trims the final speech token's audio (~40 ms of noise emitted just
before EOS) — so segment ends are already trimmed, and any inter-segment padding
we add is on top of that.

## Open items to test

1. Does `he` accept unvocalised Hebrew script, and how does it handle ambiguity
   (`בטוח` vs `בטח`) with no niqqud?
2. How much does the voice identity drift between an `en` segment and a `he`
   segment from the same `audio_prompt_path`?
3. How much silence, if any, is needed at segment joins before they stop sounding
   like cuts — the voice note's instinct is to try it and listen, which is right.
