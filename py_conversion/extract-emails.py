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

for line in sys.stdin:
    for name, address in getaddresses([line]):
        if not address or '@' not in address:
            continue
        if NO_DOT_DOMAIN.search(address):
            continue
        if not name:
            name = address.split('@')[0]
        name = canonical(name)
        address = address.lower().lstrip("'\"").rstrip("'\"")
        print(f"{name}\t{address}")
