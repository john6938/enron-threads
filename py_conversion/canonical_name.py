import re

def _perl_split(pattern, text):
    """Approximate Perl split /pattern/, text by dropping trailing empty fields."""
    parts = re.split(pattern, text)
    while parts and parts[-1] == '':
        parts.pop()
    return parts

def canonical(name):
    name = name.lower()
    name = re.sub(r'''^['\"]*''', '', name)
    name = re.sub(r'''['\"]*$''', '', name)
    name = re.sub(r'[._]', ' ', name)
    name = re.sub(r'^ *', '', name)
    name = re.sub(r' *$', '', name)
    name = re.sub(r'@.*$', '', name)
    if ',' in name:
        parts = _perl_split(r', *', name)
        name = ' '.join(reversed(parts))
    name = re.sub(r'  +', ' ', name)
    return name

def shortened(name):
    parts = _perl_split(r' ', name)
    if len(parts) > 2:
        return ' '.join((parts[0], parts[-1]))
    return name
