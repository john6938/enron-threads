#!/usr/bin/env python3
"""Extract the re-cleaned Enron RAR into a standard maildir layout.

Source structure:  <archive>/<First.Last>[Y]/known - [First.Last] - Mail_N.txt
Output structure:  corpus/rar/<first.last>/mail/N

The [Y] suffix and 'known'/'unknown' prefix are stripped.
User names are lowercased with dots preserved (matches Enron maildir convention).
"""
import re
import sys
import os
import subprocess
import tempfile
import shutil

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAR_PATH  = os.path.join(REPO_ROOT, 'Enron (re-cleaned at May 2018).rar')
OUT_ROOT  = os.path.join(REPO_ROOT, 'corpus', 'rar')

def normalize_name(raw):
    # "Andy.zipper[Y]" -> "andy.zipper"
    return re.sub(r'\[.*?\]', '', raw).strip().lower()

def list_rar_entries():
    result = subprocess.run(
        ['7z', 'l', '-ba', RAR_PATH],
        capture_output=True, text=True, check=True
    )
    entries = []
    for line in result.stdout.splitlines():
        # format: "date time attr size comp name"
        parts = line.split(None, 5)
        if len(parts) == 6:
            entries.append(parts[5])
    return entries

def main():
    if not os.path.exists(RAR_PATH):
        print(f"RAR not found: {RAR_PATH}", file=sys.stderr)
        sys.exit(1)

    # Extract everything into a temp dir, then reorganise
    tmp = tempfile.mkdtemp()
    try:
        print("Extracting RAR...")
        subprocess.run(
            ['7z', 'x', RAR_PATH, f'-o{tmp}', '-y'],
            check=True, capture_output=True
        )

        inner = os.path.join(tmp, 'Enron (re-cleaned at May 2018)')
        if not os.path.isdir(inner):
            # fallback: find the single extracted subdirectory
            inner = next(
                os.path.join(tmp, d) for d in os.listdir(tmp)
                if os.path.isdir(os.path.join(tmp, d))
            )

        users_written = {}
        for user_raw in os.listdir(inner):
            user_dir = os.path.join(inner, user_raw)
            if not os.path.isdir(user_dir):
                continue
            user = normalize_name(user_raw)
            if not user:
                continue

            out_dir = os.path.join(OUT_ROOT, user, 'mail')
            os.makedirs(out_dir, exist_ok=True)

            for fname in sorted(os.listdir(user_dir)):
                if not fname.endswith('.txt'):
                    continue
                m = re.search(r'Mail_(\d+)', fname)
                if not m:
                    continue
                num = m.group(1)
                src = os.path.join(user_dir, fname)
                dst = os.path.join(out_dir, num)
                shutil.copy2(src, dst)
                users_written[user] = users_written.get(user, 0) + 1

        print(f"Extracted {sum(users_written.values())} files across {len(users_written)} users -> corpus/rar/")
        for u, c in sorted(users_written.items()):
            print(f"  {u}: {c}")
    finally:
        shutil.rmtree(tmp)

if __name__ == '__main__':
    main()
