"""
Cut sentence-level audio clips from source.mp4 using ffmpeg.

Reads sentences_prompts.json (each item has time_start / time_end in HH:MM:SS.mmm)
and produces an mp3 per sentence.

Idempotent: skips clips that already exist.
"""

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent

# Parameterized (defaults reproduce S01E01):
#   python3 cut_clips.py [source_mp4] [sentences_json] [out_dir]
SOURCE = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "sources" / "peppa-s01e01" / "source.mp4"
SENTENCES_FILE = Path(sys.argv[2]) if len(sys.argv) > 2 else ROOT / "sentences_prompts.json"
OUT_DIR = Path(sys.argv[3]) if len(sys.argv) > 3 else ROOT / "assets" / "sentences_audio_clip"
OUT_DIR.mkdir(parents=True, exist_ok=True)


def cut_one(sent_id: str, start: str, end: str) -> tuple[str, str]:
    out = OUT_DIR / f"{sent_id}.mp3"
    if out.exists():
        return ("skip", sent_id)
    cmd = [
        "ffmpeg", "-y", "-loglevel", "error",
        "-ss", start, "-to", end,
        "-i", str(SOURCE),
        "-vn",
        "-acodec", "libmp3lame", "-b:a", "96k",
        str(out),
    ]
    try:
        subprocess.run(cmd, check=True, capture_output=True)
    except subprocess.CalledProcessError as e:
        return (f"err: {e.stderr.decode()[:120]}", sent_id)
    return ("ok", sent_id)


def main():
    if not SOURCE.exists():
        print(f"ERROR: {SOURCE} not found. Run yt-dlp first.")
        return

    spec = json.loads(SENTENCES_FILE.read_text())
    sentences = spec["sentences"]

    print(f"=== Cutting {len(sentences)} sentence clips from source.mp4 ===")
    for s in sentences:
        status, sid = cut_one(s["id"], s["time_start"], s["time_end"])
        marker = "·" if status == "skip" else ("✓" if status == "ok" else "✗")
        print(f"  {marker} {sid:6s}  [{s['time_start']} -> {s['time_end']}]  {status if status != 'ok' else ''}")

    print(f"\nDone.")
    print(f"  Sentence clips: {OUT_DIR}")


if __name__ == "__main__":
    main()
