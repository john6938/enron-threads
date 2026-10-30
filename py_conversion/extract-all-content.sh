#!/usr/bin/env bash
# Run extract-email-content.py in parallel across all user directories.
# Usage: bash py_conversion/extract-all-content.sh <maildir_root> <output_dir>
set -euo pipefail

SDIR="$(cd "$(dirname "$0")" && pwd)"

if [ $# -lt 2 ]; then
    echo "Usage: $0 <maildir_root> <output_dir>" >&2
    exit 1
fi

MAILDIR="${1%/}"
OUTDIR="$2"
COUNT=0

for d in "$MAILDIR"/*/; do
    NAME="$(basename "$d")"
    (python3 "$SDIR/extract-email-content.py" "$d" "$OUTDIR" 2>&1 \
        | sed "s/^/$NAME: /") &
    ((++COUNT))
done

echo "Waiting for $COUNT jobs..."
wait
echo "Done. $COUNT email-content files written to $OUTDIR"
