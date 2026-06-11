"""
Episode-aware asset generator: images (Seedream) + TTS (OpenAI via Zhenguanyu proxy).

Usage:
  python3 gen_episode.py <spec_dir> <episode_id> [--only=images|audio]

Asset layout (MVP 2.0):
  - L1 words are a GLOBAL pool: assets/images/<lemma>.png + assets/audio/<lemma>.mp3,
    shared across all episodes. Words flagged "reuse": true are skipped (an earlier
    episode already produced them). Cross-episode dedup is by lemma.
  - L2 chunks / L3 sentences are PER-EPISODE: assets/<episode_id>/...

Idempotent: existing files are skipped unless FORCE=1 in env.
TTS guards against truncated upstream responses via MIN_BYTES (see CLAUDE.md 5.6).
"""

import json
import os
import sys
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

ROOT = Path(__file__).parent

SEEDREAM_KEY = os.environ.get("SEEDREAM_KEY", "")
SEEDREAM_URL = os.environ.get("SEEDREAM_URL", "")

TTS_KEY = os.environ.get("TTS_API_KEY", "")
TTS_URL = os.environ.get("TTS_API_URL", "")
TTS_MODEL = "gpt-4o-mini-tts"
TTS_VOICE = os.environ.get("TTS_VOICE", "alloy")

FORCE = os.environ.get("FORCE") == "1"
MIN_BYTES = 4000
WORKERS = int(os.environ.get("GEN_WORKERS", "3"))
IMAGE_TIMEOUT = int(os.environ.get("IMAGE_TIMEOUT", "75"))


def seedream(subject: str, style: str, out_png: Path):
    if out_png.exists() and not FORCE:
        return ("skip", out_png.name)
    if not SEEDREAM_KEY or not SEEDREAM_URL:
        return ("missing SEEDREAM_KEY or SEEDREAM_URL env", out_png.name)
    prompt = f"儿童 App UI 素材：{subject}，{style}"
    payload = json.dumps({
        "model": "doubao-seedream-5-0-260128",
        "prompt": prompt,
        "size": "2048x2048",
        "watermark": False,
        "output_format": "png",
    }).encode("utf-8")
    req = urllib.request.Request(SEEDREAM_URL, data=payload, headers={
        "Authorization": f"Bearer {SEEDREAM_KEY}",
        "Content-Type": "application/json",
    }, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=IMAGE_TIMEOUT) as r:
            body = json.loads(r.read())
    except Exception as e:
        return (f"api err: {e}", out_png.name)
    data = body.get("data") or []
    if not data or "url" not in data[0]:
        return (f"no url: {str(body)[:120]}", out_png.name)
    try:
        with urllib.request.urlopen(data[0]["url"], timeout=IMAGE_TIMEOUT) as r:
            out_png.write_bytes(r.read())
    except Exception as e:
        return (f"download err: {e}", out_png.name)
    return ("ok", out_png.name)


def tts(text: str, out_mp3: Path, speed: float = 1.0):
    if out_mp3.exists() and not FORCE:
        return ("skip", out_mp3.name)
    if not TTS_KEY or not TTS_URL:
        return ("missing TTS_API_KEY or TTS_API_URL env", out_mp3.name)
    payload = json.dumps({
        "model": TTS_MODEL,
        "input": text,
        "voice": TTS_VOICE,
        "response_format": "mp3",
        "speed": speed,
    }).encode("utf-8")
    req = urllib.request.Request(TTS_URL, data=payload, headers={
        "Authorization": f"Bearer {TTS_KEY}",
        "Content-Type": "application/json",
    }, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            data = r.read()
    except Exception as e:
        return (f"err: {e}", out_mp3.name)
    if not data or len(data) < MIN_BYTES:
        return (f"tiny response ({len(data)}B < {MIN_BYTES})", out_mp3.name)
    out_mp3.write_bytes(data)
    return ("ok", out_mp3.name)


def run_pool(label: str, jobs: list) -> int:
    print(f"\n=== {label} ({len(jobs)} jobs) ===")
    ok = skip = err = 0
    with ThreadPoolExecutor(max_workers=WORKERS) as ex:
        futures = [ex.submit(j) for j in jobs]
        for f in as_completed(futures):
            status, name = f.result()
            if status == "ok":
                ok += 1
            elif status == "skip":
                skip += 1
            else:
                err += 1
                print(f"  ✗ {name:34s} {status}")
    print(f"  -> ok={ok} skip={skip} err={err}")
    return err


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    opts = [a for a in sys.argv[1:] if a.startswith("--")]
    if len(args) < 2:
        print("Usage: python3 gen_episode.py <spec_dir> <episode_id> [--only=images|audio]")
        sys.exit(1)
    spec_dir = ROOT / args[0]
    episode_id = args[1]
    only = None
    for o in opts:
        if o.startswith("--only="):
            only = o.split("=", 1)[1]
    do_img = only in (None, "images")
    do_aud = only in (None, "audio")

    prompts = json.loads((spec_dir / "prompts.json").read_text())
    chunks = json.loads((spec_dir / "chunks_prompts.json").read_text())
    sents = json.loads((spec_dir / "sentences_prompts.json").read_text())

    word_img = ROOT / "assets" / "images"
    word_aud = ROOT / "assets" / "audio"
    ep = ROOT / "assets" / episode_id
    chunk_img = ep / "chunks_images"
    chunk_aud = ep / "chunks_audio_tts"
    sent_img = ep / "sentences_images"
    sent_aud = ep / "sentences_audio_tts"
    for d in (word_img, word_aud, chunk_img, chunk_aud, sent_img, sent_aud):
        d.mkdir(parents=True, exist_ok=True)

    new_words = [w for w in prompts["words"] if not w.get("reuse")]
    reuse_words = [w for w in prompts["words"] if w.get("reuse")]
    print(f"Episode {episode_id}: {len(new_words)} new words + {len(reuse_words)} reused (global pool)")

    if do_img:
        wstyle, cstyle, sstyle = prompts["_style"], chunks["_style"], sents["_style"]
        run_pool("Word images", [
            (lambda w=w: seedream(w["subject"], wstyle, word_img / f'{w["lemma"]}.png'))
            for w in new_words
        ])
        run_pool("Chunk images", [
            (lambda c=c: seedream(c["subject"], cstyle, chunk_img / f'{c["id"]}.png'))
            for c in chunks["chunks"]
        ])
        run_pool("Sentence images", [
            (lambda s=s: seedream(s["subject"], sstyle, sent_img / f'{s["id"]}.png'))
            for s in sents["sentences"]
        ])

    if do_aud:
        wjobs = []
        for w in new_words:
            wjobs.append(lambda w=w: tts(w["lemma"], word_aud / f'{w["lemma"]}.mp3', 1.0))
            wjobs.append(lambda w=w: tts(w["lemma"], word_aud / f'{w["lemma"]}_slow.mp3', 0.75))
        run_pool("Word TTS", wjobs)
        cjobs = []
        for c in chunks["chunks"]:
            cjobs.append(lambda c=c: tts(c["text"], chunk_aud / f'{c["id"]}.mp3', 1.0))
            cjobs.append(lambda c=c: tts(c["text"], chunk_aud / f'{c["id"]}_slow.mp3', 0.75))
        run_pool("Chunk TTS", cjobs)
        sjobs = []
        for s in sents["sentences"]:
            sjobs.append(lambda s=s: tts(s["text"], sent_aud / f'{s["id"]}.mp3', 1.0))
            sjobs.append(lambda s=s: tts(s["text"], sent_aud / f'{s["id"]}_slow.mp3', 0.75))
        run_pool("Sentence TTS", sjobs)

    print("\nDone.")


if __name__ == "__main__":
    main()
