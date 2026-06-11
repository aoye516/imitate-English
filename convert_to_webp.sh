#!/bin/bash
# Convert PNG images to WebP, resize to 1024px max, quality 85. Keeps PNG originals.
# Usage: ./convert_to_webp.sh [dir ...]
# With no args, converts the default S01E01 flat dirs.
set -e
cd "$(dirname "$0")"

dirs=("$@")
if [ ${#dirs[@]} -eq 0 ]; then
    dirs=(assets/images assets/chunks_images assets/sentences_images)
fi

count=0
for dir in "${dirs[@]}"; do
    for f in "$dir"/*.png; do
        [ -f "$f" ] || continue
        out="${f%.png}.webp"
        if [ ! -f "$out" ]; then
            cwebp -quiet -q 85 -resize 1024 0 "$f" -o "$out"
            count=$((count+1))
        fi
    done
done
echo "Converted $count files"
