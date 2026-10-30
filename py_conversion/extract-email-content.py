#!/usr/bin/env python3
"""
Extract readable email content from an Enron maildir user directory.

Each thread file contains a chain of forwarded/replied emails nested inside
each other. This script splits each file at its separator boundaries, extracts
headers and body text for each component email, and writes one JSON output
file per user.

Usage:
    python3 extract-email-content.py <maildir_user_path> <output_dir>

Output:
    <output_dir>/email-content-<username>.json

Keys in the output JSON match the 'file' field in threads-<username>.json so
the UI can look up content by thread.

Each key maps to a list of emails in chronological order (oldest first), each
with fields: from, to, date, subject, body.
"""
import sys
import os
import re
import json

# Matches the separator lines that divide embedded emails within a thread file.
# Handles both Outlook ("-----Original Message-----") and
# Lotus Notes ("---- Forwarded by Name on DATE ----") formats.
SEPARATOR = re.compile(
    r'\n[ \t]*-{4,}[ \t]*(?:Original Message|Forwarded by\b[^\n]*)[ \t]*-*[ \t]*\n',
    re.IGNORECASE
)

RFC_HEADER = re.compile(r'^([A-Za-z-]+):\s*(.*)')

# Matches any header-like field inside embedded emails (Word: value).
# We only store the fields we care about; others are skipped but keep the
# parser in header-scanning mode so Cc/Bcc don't prematurely end the block.
MINI_HEADER = re.compile(r'^[ \t]*([A-Za-z-]+)[ \t]*:[ \t]*(.*)')


def parse_rfc_segment(text):
    """Parse the top-level email: RFC headers + body separated by a blank line."""
    lines = text.split('\n')
    headers = {}
    current_key = None
    body_start = len(lines)

    for i, line in enumerate(lines):
        rstripped = line.rstrip('\r')
        if rstripped == '':
            body_start = i + 1
            break
        m = RFC_HEADER.match(rstripped)
        if m:
            current_key = m.group(1)
            headers[current_key] = m.group(2)
        elif current_key and rstripped[:1] in (' ', '\t'):
            headers[current_key] += ' ' + rstripped.strip()

    body = '\n'.join(lines[body_start:]).strip()
    return {
        'from':    headers.get('From', ''),
        'to':      headers.get('To', ''),
        'date':    headers.get('Date', ''),
        'subject': headers.get('Subject', ''),
        'body':    body,
    }


def parse_embedded_segment(text):
    """
    Parse an embedded (forwarded/replied) email from plain text.
    Handles both Outlook mini-headers (From/Sent/To/Subject) and
    Lotus Notes blocks (sender name + date on separate lines, then To/Subject).
    """
    result = {'from': '', 'to': '', 'date': '', 'subject': '', 'body': ''}
    lines = text.lstrip('\n').split('\n')

    i = 0
    # Pass 1: look for Outlook-style labelled headers
    outlook_hits = 0
    body_start = 0
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped == '':
            body_start = i + 1
            break
        m = MINI_HEADER.match(line)
        if m:
            key = m.group(1).lower()
            val = m.group(2).strip()
            if key == 'sent':
                key = 'date'
            if key in result:
                result[key] = val
            outlook_hits += 1
        else:
            # Non-header line before blank line — stop scanning if we already
            # have some headers, otherwise keep going (Lotus Notes noise lines)
            if outlook_hits > 0:
                body_start = i
                break
    else:
        body_start = len(lines)

    # Pass 2: Lotus Notes fallback — if no Outlook headers found, try to
    # pick up sender name (line 0) and date (line 1) before the blank line.
    if outlook_hits == 0 and len(lines) >= 2:
        candidate_name = lines[0].strip()
        candidate_date = lines[1].strip()
        # Rough date check: contains digits and slashes or colons
        if candidate_name and re.search(r'\d', candidate_date):
            result['from'] = candidate_name
            result['date'] = candidate_date
        # To/Subject may follow after a blank line
        for j in range(2, len(lines)):
            stripped = lines[j].strip()
            if stripped == '':
                continue
            m = MINI_HEADER.match(lines[j])
            if m:
                key = m.group(1).lower()
                val = m.group(2).strip()
                if key in result:
                    result[key] = val
            else:
                body_start = j
                break

    result['body'] = '\n'.join(lines[body_start:]).strip()
    return result


def parse_thread_file(filepath):
    """
    Split a thread file into its component emails and return them
    in chronological order (oldest first).
    """
    with open(filepath, encoding='utf-8', errors='replace') as f:
        content = f.read()

    segments = SEPARATOR.split(content)

    emails = []
    for i, seg in enumerate(segments):
        if i == 0:
            emails.append(parse_rfc_segment(seg))
        else:
            emails.append(parse_embedded_segment(seg))

    emails.reverse()
    return emails


def main():
    if len(sys.argv) != 3:
        print(f'Usage: {sys.argv[0]} <maildir_user_path> <output_dir>', file=sys.stderr)
        sys.exit(1)

    user_path = os.path.realpath(sys.argv[1])
    output_dir = sys.argv[2]
    username = os.path.basename(user_path)

    result = {}
    for root, dirs, files in os.walk(user_path):
        dirs.sort()
        for fname in sorted(files):
            filepath = os.path.join(root, fname)
            result[filepath] = parse_thread_file(filepath)

    outfile = os.path.join(output_dir, f'email-content-{username}.json')
    with open(outfile, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False)

    print(f'Written {len(result)} files → {outfile}', file=sys.stderr)


if __name__ == '__main__':
    main()
