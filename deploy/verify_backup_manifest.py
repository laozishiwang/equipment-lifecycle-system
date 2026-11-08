#!/usr/bin/env python3
"""Verify the three expected backup artifacts against a strict local SHA-256 manifest."""
import hashlib
import re
import sys
from pathlib import Path

EXPECTED={'database.sql.gz','uploads.tar.gz','private-uploads.tar.gz'}
LINE=re.compile(r'([0-9a-fA-F]{64})  ([a-z0-9.-]+)')

def verify(directory):
    root=Path(directory)
    manifest=root/'SHA256SUMS'
    if manifest.is_symlink() or not manifest.is_file(): raise ValueError('missing or unsafe manifest')
    entries={}
    for line in manifest.read_text(encoding='ascii').splitlines():
        match=LINE.fullmatch(line)
        if not match: raise ValueError('malformed manifest entry')
        digest,name=match.groups()
        if name not in EXPECTED or name in entries: raise ValueError('unexpected or duplicate artifact')
        entries[name]=digest.lower()
    if set(entries)!=EXPECTED: raise ValueError('manifest does not contain all expected artifacts')
    for name,expected in entries.items():
        path=root/name
        if path.is_symlink() or not path.is_file(): raise ValueError('missing or unsafe artifact: '+name)
        digest=hashlib.sha256()
        with path.open('rb') as source:
            for chunk in iter(lambda:source.read(1024*1024),b''): digest.update(chunk)
        if digest.hexdigest()!=expected: raise ValueError('checksum mismatch: '+name)
    return len(entries)

if __name__=='__main__':
    if len(sys.argv)!=2: print('usage: verify_backup_manifest.py BACKUP_DIRECTORY',file=sys.stderr);sys.exit(2)
    try: print('verified_artifacts='+str(verify(sys.argv[1])))
    except (OSError,UnicodeError,ValueError) as error: print('backup verification failed: '+str(error),file=sys.stderr);sys.exit(1)
