#!/usr/bin/env python3
import sys
import os
import re
import json
import getopt
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.stdin.reconfigure(encoding='utf-8', errors='replace')
sys.stdout.reconfigure(encoding='utf-8')
from email.utils import getaddresses
from canonical_name import canonical, shortened

def print_object(obj):
    print(json.dumps(obj, ensure_ascii=False, indent=3, sort_keys=True))

def valid_email(email):
    if not email:
        return False
    return bool(re.fullmatch(r'[A-Za-z_.0-9-]+@[A-Za-z_-]+\.[A-Za-z_.]+', email))

def parse_email_addresses(text):
    if not text:
        return []
    results = [(name, address) for name, address in getaddresses([text]) if address and '@' in address]
    if not results:
        m = re.search(r'<([^>@]+@[^>]+?)>', text)
        if m:
            name_m = re.match(r'\s*"?([^"<]+)"?\s*<', text)
            results = [(name_m.group(1).strip() if name_m else '', m.group(1))]
    if not results:
        m = re.search(r'\[mailto:([^\]]+@[^\]]+)\]', text)
        if m:
            results = [('', m.group(1))]
    if not results:
        m = re.search(r'[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}', text)
        if m:
            results = [('', m.group(0))]
    return results

def main():
    try:
        opts, args = getopt.getopt(sys.argv[1:], 'fh:a:')
    except getopt.GetoptError as err:
        print(err, file=sys.stderr)
        sys.exit(2)
    show_failures = False
    min_hops = 3
    address_file = None
    for opt, value in opts:
        if opt == '-f':
            show_failures = True
        elif opt == '-h':
            try: parsed = int(value)
            except ValueError: parsed = 0
            min_hops = parsed or 3
        elif opt == '-a':
            address_file = value
    show_threads = not show_failures
    addresses = {}
    if address_file:
        with open(address_file, 'r', encoding='utf-8', errors='replace') as f:
            for line in f:
                line = line.rstrip('\r\n')
                parts = line.split('\t')
                if len(parts) >= 2:
                    addresses[parts[0]] = parts[1]
    if show_threads:
        print('[')
    last, hops, failures = [], [], []
    conv = None
    from_ = ''
    failed = found = lineno = 0
    first = True
    for line in sys.stdin:
        lineno += 1
        if line.startswith('FFFFIIIILLLLEEEE'):
            if show_threads and len(hops) > min_hops:
                if not first:
                    print(',')
                first = False
                print_object({'file': conv, 'hops': hops, 'skipped': len(failures)})
            if show_failures and failures:
                print_object({'file': conv, 'succeeded': len(hops), 'failures': failures})
            hops, failures = [], []
            parts = line.split()
            conv = parts[1] if len(parts) > 1 else None
            lineno = 0
            continue
        if re.search(r'(?<!-)From:', line):
            from_ = re.sub(r'.*From: (.*)', r'\1', line)
        elif re.search(r'(?<!-)Forwarded by', line):
            from_ = re.sub(r'.*Forwarded by (.*)', r'\1', line)
        if re.search(r'(?<!-)To:', line):
            if not from_:
                before = re.sub(r'(.*)To:.*', r'\1', line)
                before = re.sub(r'^\s*', '', before)
                before = re.sub(r'\s*$', '', before)
                if before:
                    last.append(before)
                flast = [item for item in last if not (re.search(r'^\s+$', item) or re.search(r'^\s*Sent by:.*$', item))]
                if len(flast) == 1:
                    from_ = re.sub(r'^\s*', '', flast[0])
                elif len(flast) > 1 and re.search(r'^\s*[0-9]+/[0-9]+/[0-9]+', flast[-1]):
                    from_ = re.sub(r'^\s*', '', flast[-2])
                else:
                    for cand in flast:
                        emails = parse_email_addresses(cand)
                        if emails:
                            from_ = emails[0][1]
                            break
            line = re.sub(r'^.*To:\s*', '', line)
            line = re.sub(r'\s*$', '', line)
            rawfrom = from_ if from_ else None
            canonical_name = ''
            source = ''
            if from_:
                from_ = re.sub(r'^\s*', '', from_)
                from_ = re.sub(r'\s*$', '', from_)
                source = 'valid'
                if not valid_email(from_):
                    from_ = re.sub(r' on .*$', '', from_)
                    from_ = re.sub(r'^=09', '', from_)
                    emails = parse_email_addresses(from_)
                    if emails and valid_email(emails[0][1]):
                        from_ = emails[0][1]
                        source = 'email'
                    else:
                        match = re.match(r'''^[A-Za-z, "'-]+''', from_)
                        if match:
                            fromname = re.sub(r' +$', '', match.group(0))
                            from_ = fromname
                            canonical_name = canonical(from_)
                            from_ = addresses.get(canonical_name)
                            if not from_:
                                canonical_name = shortened(canonical_name)
                                from_ = addresses.get(canonical_name)
                            source = 'lookup'
                        else:
                            from_ = None
            if from_:
                found += 1
                hops.append({'rawfrom': rawfrom, 'from': from_.lower(), 'to': line, 'line': lineno, 'source': source})
            else:
                failed += 1
                failures.append({'canonical': canonical_name, 'recent': list(last), 'raw': rawfrom, 'to': line})
            from_ = ''
        last.append(line)
        while len(last) > 5:
            last.pop(0)
    if show_threads:
        print(']')
    if show_failures:
        print(f'found {found}')
        print(f'failed {failed}')

if __name__ == '__main__':
    main()
