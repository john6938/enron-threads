#!/usr/bin/env python3
"""Extract the re-cleaned Enron RAR into a standard maildir layout.

Source structure:  <archive>/<First.Last>[Y]/known - [First.Last] - Mail_N.txt
Output structure:  corpus/rar/<first.last>/mail/N

The [Y] suffix and 'known'/'unknown' prefix are stripped.
User names are lowercased with dots preserved (matches Enron maildir convention).
"""
import rarfile
import re
import sys
import os

def normalize_name(raw):
    # "Andy.zipper[Y]" -> "andy.zipper"
    return re.sub(r'\[.*?\]', '', raw).strip().lower()

def main():
    rar_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                            'Enron (re-cleaned at May 2018).rar')
    out_root = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                            'corpus', 'rar')

    if not os.path.exists(rar_path):
        print(f"RAR not found: {rar_path}", file=sys.stderr)
        sys.exit(1)

    rf = rarfile.RarFile(rar_path)
    infos = [i for i in rf.infolist() if not i.is_dir() and i.filename.endswith('.txt')]

    users_written = {}
    for info in infos:
        parts = info.filename.split('/')
        if len(parts) < 3:
            continue
        user_raw = parts[1]          # "Andy.zipper[Y]"
        filename  = parts[2]         # "known - [Andy.zipper] - Mail_1.txt"

        user = normalize_name(user_raw)
        m = re.search(r'Mail_(\d+)', filename)
        if not m:
            continue
        num = m.group(1)

        out_dir = os.path.join(out_root, user, 'mail')
        os.makedirs(out_dir, exist_ok=True)
        out_path = os.path.join(out_dir, num)

        data = rf.read(info)
        with open(out_path, 'wb') as f:
            f.write(data)
        users_written[user] = users_written.get(user, 0) + 1

    print(f"Extracted {sum(users_written.values())} files across {len(users_written)} users → corpus/rar/")
    for u, c in sorted(users_written.items()):
        print(f"  {u}: {c}")

if __name__ == '__main__':
    main()
