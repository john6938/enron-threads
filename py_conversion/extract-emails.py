#!/usr/bin/env python3
import sys
import os
import re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.stdin.reconfigure(encoding='utf-8', errors='replace')
sys.stdout.reconfigure(encoding='utf-8')
from email.utils import getaddresses
from canonical_name import canonical

NO_DOT_DOMAIN = re.compile(r'@[^.]*$')
ANGLE_ADDR = re.compile(r'<([^>@\s]+@[^>]+?)>')
NAME_BEFORE_ANGLE = re.compile(r'"([^"]+)"\s*$|([A-Za-z][A-Za-z0-9 .-]*)\s*$')
ENRON_FWD_ADDR = re.compile(r'\b([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,})\s+on\s+\d')

for line in sys.stdin:
    emitted = False
    for name, address in getaddresses([line]):
        if not address or '@' not in address:
            continue
        if NO_DOT_DOMAIN.search(address):
            continue
        emitted = True
        if not name:
            name = address.split('@')[0]
        name = canonical(name)
        address = address.lower().lstrip("'\"").rstrip("'\"")
        print(f"{name}\t{address}")
    if not emitted:
        # Fallback for "Name <email>@GATEWAY" patterns (Enron mail gateway wrapping)
        for m in ANGLE_ADDR.finditer(line):
            addr = m.group(1)
            if NO_DOT_DOMAIN.search(addr):
                continue
            nm = NAME_BEFORE_ANGLE.search(line[:m.start()])
            name_part = (nm.group(1) or nm.group(2) or '').strip() if nm else ''
            name_part = canonical(name_part) if name_part else canonical(addr.split('@')[0])
            print(f"{name_part}\t{addr.lower()}")
            emitted = True
    if not emitted:
        # Fallback for "email@domain on DATE" forwarded-message headers
        m = ENRON_FWD_ADDR.search(line)
        if m:
            addr = m.group(1)
            if not NO_DOT_DOMAIN.search(addr):
                name_part = canonical(addr.split('@')[0])
                print(f"{name_part}\t{addr.lower()}")
