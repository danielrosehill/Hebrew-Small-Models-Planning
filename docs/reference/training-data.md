# Training data — what already exists

Verified 2026-09-22. Two corpora already exist and neither was created for this
project. Together they are probably enough to train the stage-1 classifier without
recording anything new.

## A. `danielrosehill/English-Hebrew-Mixed-Sentences` — the labelled corpus

Hugging Face dataset, **public**, MIT, last modified 2025-11-17.
<https://huggingface.co/datasets/danielrosehill/English-Hebrew-Mixed-Sentences>

This is the "Hebrish" dataset behind the `danielrosehill/Whisper-Hebrish` fine-tune
(base `openai/whisper-large-v3-turbo`, MIT, DOI 10.57967/hf/7019). It is the dataset
the voice note refers to as "a few hundred examples" — the exact ID, recorded here
because the note did not name it.

### Actual contents (read from the repo, not the README)

| | |
| --- | --- |
| Records | **516** |
| Splits | `whisper_train.jsonl` 398 / `whisper_validation.jsonl` 58 / `whisper_test.jsonl` 60 |
| Audio | 516 `.wav` under `sentences/audio/`, **31.4 minutes** total |
| Labelled with a Hebrew term | 474 |
| `hebrew_word` null | 42 |
| Distinct terms | **139** (51 multi-token, 15 appear once) |
| Categories | 29 (`general` 104, `places` 66, `religious` 51, `finance` 28, `shopping` 27, `transportation` 27 …) |

Record schema:

```json
{"id": "1_3", "audio_filepath": "sentences/audio/1_3.wav",
 "text": "Opening a bank account in Israel requires a few documents, including a passport and a teudat zehut.",
 "duration_seconds": 6.578, "language": "en-he",
 "hebrew_word": "teudat zehut", "category": "documents"}
```

### Three things to know before using it

**The README is stale.** It documents `metadata.json`, `hebrew_words_list.csv` and
MP3 audio. None of those exist — the repo has three JSONL splits and WAV audio.
Fetching the paths the README names returns `Entry not found`. Fix the README while
you are in there.

**The labels were produced by substring search, and 114 of 474 are wrong.**
Corrected 2026-09-22 — an earlier version of this document said every label is a
verbatim substring of its sentence with zero exceptions, and concluded that spans
derive mechanically. The substring test passes, but it is the wrong test: passing it
is precisely what a substring-generated label does. Under **word-boundary** matching:

| | Count | Of 474 labelled |
| --- | --- | --- |
| Label aligns with a real word | 360 | 76% |
| **Label matches only inside another word** | **114** | **24%** |

`hi` was labelled from *t**hi**nk*; `har` from *P**har**m*; `ma` from *__ma__shav*;
`gan` from *maz**gan***; `ach` from *m**ach**som*; `chool` from *s**chool***. In every
one of those 114 records the real Hebrew term — *dud*, *mashkanta*, *mirsham*,
*tlush*, *maskoret*, *hashmal*, *chufshat leida* — **is not labelled at all**.

The contamination reaches the term list too: 12 of the 139 distinct terms
(`ach ani atem ein har hi ken latke lo ma mi supermarket`) never occur as whole words
anywhere in the corpus. They exist only as bad labels. A further 17 are ordinary
English words (`at`, `hi`, `lo`, `ken`, `baby`, `chicken soup`, `supermarket` …), so
matching them fires on genuine English.

So the corpus needs real annotation, not a mechanical conversion. That work is under
way in
[**Hebrew-Latin-Token-Classifier**](https://github.com/danielrosehill/Hebrew-Latin-Token-Classifier).

**The under-labelling is separate and additional.** The schema allows exactly one
`hebrew_word` per record, but sentences contain more. Matching the 117 non-quarantined
terms back over the corpus finds 86 further candidate spans that no label covers, and
all **42** null-label records do contain Hebrew — their terms (*10 Bis*, *dud*,
*motzash*, *Zol Stock*) are absent from the lexicon entirely, including two brand
names, a category the lexicon does not model.

**Net:** of 516 records, 360 carry a usable label. The other 156 need a human.

## B. The My Weird Prompts transcript corpus — the in-domain corpus

This is the corpus the model will actually run against in production, so it is both
the best source of realistic examples and the right evaluation set.

| Location | What |
| --- | --- |
| `~/repos/github/mwp-podcast/My-Weird-Prompts/website/public/transcripts/` | **4,295 `.txt` files**, 18,510,772 words, 116 MB. One per episode, named by slug |
| `~/repos/github/mwp-podcast/datasets-exploration/data/2026-09-01/turns.parquet` | One row **per speaker turn** — the right granularity for this task. 72.5 MB |
| `~/repos/github/mwp-podcast/datasets-exploration/data/2026-09-01/episodes.parquet` | One row per episode + text stats |
| HF `My-Weird-Prompts/transcripts` | Public, CC-BY-4.0. The parquet files are gitignored local caches of it |

Canonical store is a Supabase Postgres `episodes.transcript` column; the `.txt` tree
is the largest on-disk copy. Format is blank-line-separated paragraphs, each prefixed
`Speaker: `. Turn segmentation logic:
`My-Weird-Prompts/pipeline/scripts/build_transcript_corpus.py:305-342`.

### Hebrew density — measured, not assumed

Word-boundary grep over all 4,295 files. Selected counts (files / occurrences):

| Term | Files | Occurrences |
| --- | --- | --- |
| shekels | 257 | 1,307 |
| shekel | 148 | 761 |
| Knesset | 161 | 561 |
| haredi | 64 | 542 |
| Shabbat | 67 | 426 |
| kosher | 42 | 228 |
| hummus | 57 | 202 |
| mamad | 34 | 206 |
| kibbutz | 49 | 138 |
| shuk | 26 | 146 |
| yeshiva | 33 | 120 |
| aliyah | 29 | 109 |
| arnona | 25 | 91 |
| Bituach Leumi | 7 | 8 |
| challah | 5 | 8 |
| Mas Hachnasa | 1 | 1 |
| makolet | 1 | 1 |
| balagan | 1 | 1 |
| sababa / yalla | 4 / 4 | 4 / 4 |
| beseder, kol hakavod, metapelet, sabich, chevre | 0 | 0 |

**The corpus is essentially 100% Latin transliteration**: Hebrew-script characters
(`֐-׿`) appear in only **3 of 4,295 files**.

**Assessment.** The distribution is heavily skewed to the institutional and religious
register, which is exactly the half the TTS already half-knows. The colloquial
register the voice note cares most about — *makolet*, *balagan*, *beseder* — is
single-digit or absent. So:

- The MWP corpus is excellent for **evaluation** and for **mining realistic
  negatives** (English words that look Hebrew-ish, proper nouns, place names).
- It is **not sufficient on its own for positives** in the colloquial register.
  Synthetic generation or a lexicon is still needed there, as the voice note
  suspected.
- Note the corpus is 18.5M words and the whole point is that Hebrew terms are rare
  in it. A random sample will be almost all negatives; sample *around lexicon hits*
  instead, then review.

## Derived: the lexicon

A term list is the connective tissue between A and B and the likeliest fast win:
139 terms from the labelled dataset, plus everything the grep above found in MWP.
Store it as a first-class artefact with Hebrew script alongside each Latin form —
at which point it doubles as the stage-2 lookup table, and stage 2 may not need a
model at all for the words that actually occur.
