"""
Combine all sources into a single lesson.json for the frontend.

Inputs:
  - prompts.json              (54 word prompts, with skip_image flags)
  - words_meaning.json        (Chinese meanings + spelling visibility)
  - chunks_prompts.json       (24 chunks)
  - sentences_prompts.json    (16 sentences)
  - out/vocab.json            (lemma frequencies)

Output:
  - out/lesson.json
"""

import json
import random
import sys
from pathlib import Path

ROOT = Path(__file__).parent

# Parameterized (defaults reproduce the original S01E01 build):
#   python3 build_lesson.py [spec_dir] [vocab_json] [episode_id] [title] [ep_asset_prefix] [out_path] [seen_words_json]
# L1 word assets are always the GLOBAL pool (assets/audio, assets/images), shared
# across episodes. Chunk/sentence assets live under ep_asset_prefix (per-episode).
SPEC_DIR = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT
VOCAB_PATH = Path(sys.argv[2]) if len(sys.argv) > 2 else (ROOT / "out" / "vocab.json")
EPISODE_ID = sys.argv[3] if len(sys.argv) > 3 else "peppa-s01e01"
TITLE = sys.argv[4] if len(sys.argv) > 4 else "Muddy Puddles"
EP_ASSET = sys.argv[5] if len(sys.argv) > 5 else "assets"
OUT = Path(sys.argv[6]) if len(sys.argv) > 6 else (ROOT / "out" / "lesson.json")
SEEN_WORDS_PATH = Path(sys.argv[7]) if len(sys.argv) > 7 else None

prompts = json.loads((SPEC_DIR / "prompts.json").read_text())
meanings = json.loads((SPEC_DIR / "words_meaning.json").read_text())["words"]
chunks_spec = json.loads((SPEC_DIR / "chunks_prompts.json").read_text())
sents_spec = json.loads((SPEC_DIR / "sentences_prompts.json").read_text())
vocab = json.loads(VOCAB_PATH.read_text())

# Build freq lookup from vocab.json (list of entries with lemma/count)
freq_lookup = {entry["lemma"]: entry["count"] for entry in vocab}
seen_words = set(json.loads(SEEN_WORDS_PATH.read_text())) if SEEN_WORDS_PATH and SEEN_WORDS_PATH.exists() else set()


def build_distractors(words):
    """For each word, pick 3 distractor words (visually plausible alternatives).

    Strategy: prefer same frequency tier, prefer ones with images.
    """
    imageable = [w["lemma"] for w in words if not w.get("skip_image")]
    out = {}
    for w in words:
        lemma = w["lemma"]
        pool = [other for other in imageable if other != lemma]
        random.seed(hash(lemma) & 0x7FFFFFFF)
        out[lemma] = random.sample(pool, k=min(3, len(pool)))
    return out


def main():
    words_out = []
    for w in prompts["words"]:
        lemma = w["lemma"]
        m = meanings.get(lemma, {})
        skip_img = w.get("skip_image", False)
        words_out.append({
            "lemma": lemma,
            "freq": freq_lookup.get(lemma, 0),
            "audio": f"assets/audio/{lemma}.mp3",
            "audio_slow": f"assets/audio/{lemma}_slow.mp3",
            "image": None if skip_img else f"assets/images/{lemma}.webp",
            "skip_image": skip_img,
            "meaning_zh": m.get("meaning_zh", ""),
            "spelling_visible": m.get("spelling_visible", True),
            "reused_from_prior": bool(w.get("reuse")),
        })

    distractors = build_distractors(prompts["words"])
    selected_lemmas = {w["lemma"] for w in prompts["words"]}
    chunk_lemmas = set()
    for c in chunks_spec["chunks"]:
        chunk_lemmas.update(c.get("covers_words", []))
    sentence_lemmas = set()
    for s in sents_spec["sentences"]:
        sentence_lemmas.update(s.get("key_words", []))

    # Data-only episode vocabulary for future review scheduling. This includes
    # selected L1 cards plus words referenced by L2/L3, even if the current UI
    # hides already-mastered repeated words.
    episode_lemmas = sorted(selected_lemmas | chunk_lemmas | sentence_lemmas)
    episode_words = []
    for lemma in episode_lemmas:
        m = meanings.get(lemma, {})
        episode_words.append({
            "lemma": lemma,
            "freq": freq_lookup.get(lemma, 0),
            "is_new": lemma not in seen_words,
            "has_card": lemma in selected_lemmas,
            "meaning_zh": m.get("meaning_zh", ""),
        })

    chunks_out = []
    for c in chunks_spec["chunks"]:
        cid = c["id"]
        chunks_out.append({
            "id": cid,
            "text": c["text"],
            "meaning_zh": c["meaning_zh"],
            "audio_tts": f"{EP_ASSET}/chunks_audio_tts/{cid}.mp3",
            "audio_tts_slow": f"{EP_ASSET}/chunks_audio_tts/{cid}_slow.mp3",
            "image": f"{EP_ASSET}/chunks_images/{cid}.webp",
            "covers_words": c.get("covers_words", []),
        })

    sentences_out = []
    for s in sents_spec["sentences"]:
        sid = s["id"]
        sentences_out.append({
            "id": sid,
            "text_admin_only": s["text"],
            "meaning_zh": s["meaning_zh"],
            "audio_tts": f"{EP_ASSET}/sentences_audio_tts/{sid}.mp3",
            "audio_tts_slow": f"{EP_ASSET}/sentences_audio_tts/{sid}_slow.mp3",
            "audio_clip": f"{EP_ASSET}/sentences_audio_clip/{sid}.mp3",
            "image": f"{EP_ASSET}/sentences_images/{sid}.webp",
            "chunks": s.get("chunks", []),
            "key_words": s.get("key_words", []),
            "time_start": s["time_start"],
            "time_end": s["time_end"],
        })

    lesson = {
        "id": EPISODE_ID,
        "title": TITLE,
        "level": 1,
        "duration_seconds": 300,
        "words": words_out,
        "episode_words": episode_words,
        "new_words": [w["lemma"] for w in episode_words if w["is_new"]],
        "reused_words": [w["lemma"] for w in episode_words if not w["is_new"]],
        "chunks": chunks_out,
        "sentences": sentences_out,
        "distractors": distractors,
    }

    OUT.write_text(json.dumps(lesson, ensure_ascii=False, indent=2))
    print(f"Built {OUT}")
    print(f"  words: {len(words_out)}  (with image: {sum(1 for w in words_out if not w['skip_image'])})")
    print(f"  chunks: {len(chunks_out)}")
    print(f"  sentences: {len(sentences_out)}")
    print(f"  distractor entries: {len(distractors)}")


if __name__ == "__main__":
    main()
