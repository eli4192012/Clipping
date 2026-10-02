"""Human-readable download names without changing internal export paths."""
import re
import unicodedata


def clip_filename(title, extension='mp4'):
    if extension not in ('mp4','srt'):
        raise ValueError('Unsupported download format')
    name=unicodedata.normalize('NFC',str(title or ''))
    name=''.join(c for c in name if not unicodedata.category(c).startswith('C'))
    name=re.sub(r'[<>:"/\\|?*]+',' - ',name)
    name=re.sub(r'\s+',' ',name).strip(' .-')
    name=re.sub(r'\.(mp4|srt)$','',name,flags=re.I).strip(' .-')
    # Leave ample room for the extension and browser-added duplicate suffixes.
    while len(name.encode('utf-8'))>160:name=name[:-1]
    name=name.rstrip(' .-') or 'Video highlight'
    if re.match(r'^(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(?:\.|$)',name,re.I):name='Clip - '+name
    return name+'.'+extension
