"""
Parse Peppa Pig S01E01 VTT subtitles to extract:
- Clean transcript (deduplicated, in order)
- Unique vocabulary with frequency
- Word-level timestamps (for future audio slicing)

Run: python3 parse_vtt.py
"""

import re
import sys
import json
from collections import Counter, OrderedDict
from pathlib import Path

# Usage: python3 parse_vtt.py [vtt_path] [out_dir] [title]
# Defaults reproduce the original S01E01 behavior.
_DEFAULT_VTT = Path(__file__).parent / "sources" / "peppa-s01e01" / "captions.en.vtt"
VTT_FILE = Path(sys.argv[1]) if len(sys.argv) > 1 else _DEFAULT_VTT
OUT_DIR = Path(sys.argv[2]) if len(sys.argv) > 2 else (Path(__file__).parent / "out")
TITLE = sys.argv[3] if len(sys.argv) > 3 else "Peppa Pig S01E01 · Muddy Puddles"
OUT_DIR.mkdir(parents=True, exist_ok=True)


def parse_vtt(path: Path):
    """
    Returns:
      transcript_lines: list of {start, end, text} unique caption lines in order
      word_timings: list of {word, time} for every word occurrence with a timestamp tag
    """
    raw = path.read_text(encoding="utf-8")

    # split into cues
    blocks = re.split(r"\n\n+", raw)

    transcript_lines = []
    word_timings = []
    seen_lines = set()

    cue_re = re.compile(r"(\d{2}:\d{2}:\d{2}\.\d{3})\s*-->\s*(\d{2}:\d{2}:\d{2}\.\d{3})")
    inline_ts_re = re.compile(r"<(\d{2}:\d{2}:\d{2}\.\d{3})><c>\s*([^<]+?)\s*</c>")

    for block in blocks:
        m = cue_re.search(block)
        if not m:
            continue
        start, end = m.group(1), m.group(2)

        # text part: lines after the cue header
        lines = block.split("\n")
        # drop header lines (anything matching cue_re)
        text_lines = [ln for ln in lines if not cue_re.search(ln) and ln.strip()]
        if not text_lines:
            continue

        # Strip the leading word (which has no inline timestamp) + inline-tagged words
        full = " ".join(text_lines).strip()

        # Extract every <ts><c>word</c> as a word timing
        for ts, word in inline_ts_re.findall(full):
            word_timings.append({"word": word.strip().lower(), "time": ts})

        # Remove inline tags to get plain text
        plain = re.sub(r"<\d{2}:\d{2}:\d{2}\.\d{3}>", "", full)
        plain = re.sub(r"</?c>", "", plain).strip()
        plain = re.sub(r"\s+", " ", plain)

        # Skip duplicate caption lines (YouTube emits each line several times)
        if plain in seen_lines or not plain:
            continue
        seen_lines.add(plain)

        transcript_lines.append({"start": start, "end": end, "text": plain})

    return transcript_lines, word_timings


def clean_word(w: str) -> str:
    """lower + strip punctuation, but keep apostrophes inside words (don't, it's)"""
    w = w.lower().strip()
    w = re.sub(r"^[^a-z']+|[^a-z']+$", "", w)
    return w


# Words to skip entirely (subtitle markers, musical interjections)
NON_VOCAB = {"music", "laughter", "applause", "cheering"}

# Manual normalization for things our naive rules would mangle or split incorrectly
LEMMA_OVERRIDES = {
    "this": "this", "his": "his", "is": "is", "us": "us", "as": "as",
    "has": "has", "was": "was", "yes": "yes", "boss": "boss",
    "having": "have", "been": "be",
    "mommy": "mummy",  # merge US/UK variants
    # Common auto-caption / light-lemmatizer artifacts seen in S01E03-E10.
    # These captions are downloaded VTTs, but most are YouTube auto captions.
    "cooky": "cookie",
    "glasse": "glasses",
    "poly": "polly",
    "suzie": "susie",
    "pepper": "peppa",
    "someth": "something",
    "anyth": "anything",
    "everyth": "everything",
    "alway": "always",
    "upstair": "upstairs",
    "finishe": "finish",
    "ridiculou": "ridiculous",
    "mak": "make",
    "goe": "go",
    "hid": "hide",
}


def lemma(w: str) -> str:
    """Light lemmatization for plural / 3rd-person / -ing / -ed."""
    if w in LEMMA_OVERRIDES:
        return LEMMA_OVERRIDES[w]
    if len(w) <= 3:
        return w
    if w.endswith("ies") and len(w) > 4:
        return w[:-3] + "y"
    if w.endswith("ing") and len(w) > 5:
        base = w[:-3]
        if len(base) >= 2 and base[-1] == base[-2]:
            return base[:-1]
        return base
    if w.endswith("ed") and len(w) > 4:
        base = w[:-2]
        if len(base) >= 2 and base[-1] == base[-2]:
            return base[:-1]
        return base
    if w.endswith("s") and not w.endswith("ss") and not w.endswith("'s"):
        return w[:-1]
    return w


def build_vocab(transcript_lines, word_timings):
    # Use the deduplicated transcript text as the source of truth for word counting
    all_words = []
    for line in transcript_lines:
        # Strip [Music] / [Laughter] tags before tokenizing
        cleaned = re.sub(r"\[[^\]]+\]", " ", line["text"])
        for tok in cleaned.split():
            cw = clean_word(tok)
            if cw and re.search(r"[a-z]", cw) and cw not in NON_VOCAB:
                all_words.append(cw)

    # Map first-occurrence time using word_timings (best-effort)
    first_time = {}
    for wt in word_timings:
        cw = clean_word(wt["word"])
        if cw and cw not in first_time:
            first_time[cw] = wt["time"]

    # Group by lemma
    by_lemma = OrderedDict()
    for w in all_words:
        L = lemma(w)
        if L not in by_lemma:
            by_lemma[L] = {"lemma": L, "forms": Counter(), "count": 0, "first_time": None}
        by_lemma[L]["forms"][w] += 1
        by_lemma[L]["count"] += 1
        if by_lemma[L]["first_time"] is None and w in first_time:
            by_lemma[L]["first_time"] = first_time[w]

    vocab = []
    for L, info in by_lemma.items():
        vocab.append({
            "lemma": L,
            "count": info["count"],
            "forms": dict(info["forms"]),
            "first_time": info["first_time"],
        })
    vocab.sort(key=lambda x: (-x["count"], x["lemma"]))
    return vocab


# Function words: pronouns, articles, auxiliaries, prepositions, conjunctions,
# common contractions, light verbs, demonstratives. Hard to "image" — handle with
# context training (L2) rather than image-audio cards.
FUNCTION_WORDS = {
    # pronouns
    "i", "you", "he", "she", "it", "we", "they", "me", "him", "her", "us", "them",
    "my", "your", "his", "its", "our", "their", "mine", "yours", "ours", "theirs",
    "myself", "yourself", "himself", "herself", "itself", "ourselves", "themselves",
    "this", "that", "these", "those",
    "i'm", "you're", "he's", "she's", "it's", "we're", "they're",
    "i've", "you've", "we've", "they've", "i'll", "you'll", "we'll",
    # articles / determiners
    "a", "an", "the", "some", "any", "no", "every", "all", "each", "both",
    "much", "many", "few", "several", "other", "another",
    # auxiliaries / modals / be / have / do
    "is", "am", "are", "was", "were", "be", "been", "being",
    "has", "have", "had", "having",
    "do", "does", "did", "doing", "done",
    "will", "would", "shall", "should", "can", "could", "may", "might", "must",
    "let", "let's",
    # conjunctions
    "and", "but", "or", "nor", "yet", "so", "because", "if", "when", "while",
    "as", "than", "though", "although", "since", "before", "after", "until",
    # prepositions
    "of", "in", "on", "at", "to", "for", "with", "by", "from", "into", "onto",
    "out", "up", "down", "over", "under", "through", "between", "about",
    "along", "around", "across",
    # common adverbs / particles
    "not", "n't", "very", "too", "also", "just", "only", "really", "well",
    "yes", "no", "ok", "okay", "oh", "ah", "uh", "hi", "hello",
    "here", "there", "where", "what", "who", "how", "why", "which", "whose",
    "now", "then", "today", "tomorrow", "yesterday",
    # filler
    "there's", "here's", "what's", "that's",
}


def classify(lem: str) -> str:
    return "function" if lem in FUNCTION_WORDS else "content"


def main():
    transcript_lines, word_timings = parse_vtt(VTT_FILE)
    vocab = build_vocab(transcript_lines, word_timings)
    for v in vocab:
        v["type"] = classify(v["lemma"])

    # Write transcript
    with (OUT_DIR / "transcript.txt").open("w") as f:
        for line in transcript_lines:
            f.write(f"[{line['start']}] {line['text']}\n")

    # Write vocab as JSON (full info)
    with (OUT_DIR / "vocab.json").open("w") as f:
        json.dump(vocab, f, indent=2, ensure_ascii=False)

    content = [v for v in vocab if v["type"] == "content"]
    function = [v for v in vocab if v["type"] == "function"]

    # Write a human-readable vocab list, split by type
    with (OUT_DIR / "vocab.md").open("w") as f:
        f.write(f"# {TITLE} - Vocabulary\n\n")
        f.write(f"- **Unique lemmas:** {len(vocab)}\n")
        f.write(f"- **Content words:** {len(content)} (image-able, L1 cards)\n")
        f.write(f"- **Function words:** {len(function)} (context-only, L2 training)\n")
        f.write(f"- **Total word tokens:** {sum(v['count'] for v in vocab)}\n\n")

        f.write("---\n\n## Content Words (build L1 cards from these)\n\n")
        f.write("| # | Lemma | Count | Forms | First @ |\n")
        f.write("|---|---|---|---|---|\n")
        for i, v in enumerate(content, 1):
            forms = ", ".join(sorted(v["forms"].keys()))
            ft = v["first_time"] or "-"
            f.write(f"| {i} | **{v['lemma']}** | {v['count']} | {forms} | {ft} |\n")

        f.write("\n---\n\n## Function Words (skip image cards, learn through context)\n\n")
        f.write("| # | Lemma | Count | Forms |\n")
        f.write("|---|---|---|---|\n")
        for i, v in enumerate(function, 1):
            forms = ", ".join(sorted(v["forms"].keys()))
            f.write(f"| {i} | **{v['lemma']}** | {v['count']} | {forms} |\n")

    # Write word-timings (for later audio slicing)
    with (OUT_DIR / "word_timings.json").open("w") as f:
        json.dump(word_timings, f, indent=2, ensure_ascii=False)

    print(f"✓ transcript:    {OUT_DIR / 'transcript.txt'}")
    print(f"✓ vocab (json):  {OUT_DIR / 'vocab.json'}")
    print(f"✓ vocab (md):    {OUT_DIR / 'vocab.md'}")
    print(f"✓ word timings:  {OUT_DIR / 'word_timings.json'}")
    print()
    print(f"Caption lines (deduped):  {len(transcript_lines)}")
    print(f"Word tokens:              {sum(v['count'] for v in vocab)}")
    print(f"Unique lemmas:            {len(vocab)}")
    print(f"  - content:              {len(content)}")
    print(f"  - function:             {len(function)}")
    print(f"\nTop 20 content words (your L1 deck):")
    for v in content[:20]:
        print(f"  {v['count']:3d}  {v['lemma']}")


if __name__ == "__main__":
    main()
