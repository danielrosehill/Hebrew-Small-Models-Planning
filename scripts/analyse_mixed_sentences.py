#!/usr/bin/env python3
"""Analyse danielrosehill/English-Hebrew-Mixed-Sentences as classifier training data.

Downloads the three JSONL splits from Hugging Face and reports label coverage,
span alignability and the under-labelling problem described in
docs/reference/training-data.md.

Usage:  python3 scripts/analyse_mixed_sentences.py
Needs:  network access; no HF token (the dataset is public).
"""
import collections
import json
import re
import urllib.request

BASE = ("https://huggingface.co/datasets/danielrosehill/"
        "English-Hebrew-Mixed-Sentences/resolve/main")
SPLITS = ["whisper_train", "whisper_validation", "whisper_test"]


def load():
    records = []
    for split in SPLITS:
        with urllib.request.urlopen(f"{BASE}/{split}.jsonl") as fh:
            rows = [json.loads(line) for line in fh.read().decode().splitlines() if line.strip()]
        print(f"{split}: {len(rows)}")
        records += rows
    return records


def main():
    records = load()
    labelled = [r for r in records if r["hebrew_word"]]
    lexicon = sorted({r["hebrew_word"].lower() for r in labelled}, key=len, reverse=True)
    pattern = re.compile(
        r"(?<!\w)(" + "|".join(re.escape(w) for w in lexicon) + r")(?!\w)", re.I)

    counts = collections.Counter(r["hebrew_word"] for r in labelled)
    unlabelled_spans = 0
    records_under_labelled = 0
    for r in records:
        hits = {m.group(1).lower() for m in pattern.finditer(r["text"])}
        label = {r["hebrew_word"].lower()} if r["hebrew_word"] else set()
        missing = hits - label
        if missing:
            unlabelled_spans += len(missing)
            records_under_labelled += 1

    print(f"\nrecords                     {len(records)}")
    print(f"labelled                    {len(labelled)}")
    print(f"null hebrew_word            {len(records) - len(labelled)}")
    print(f"distinct terms              {len(counts)}")
    print(f"  multi-token               {sum(1 for k in counts if ' ' in k)}")
    print(f"  seen once only            {sum(1 for k, v in counts.items() if v == 1)}")
    print(f"categories                  {len({r['category'] for r in records})}")
    print(f"audio minutes               {sum(r['duration_seconds'] for r in records) / 60:.1f}")
    non_verbatim = [r for r in labelled if r["hebrew_word"].lower() not in r["text"].lower()]
    print(f"labels not verbatim in text {len(non_verbatim)}")
    print(f"under-labelled records      {records_under_labelled} "
          f"({unlabelled_spans} unlabelled spans)")


if __name__ == "__main__":
    main()
