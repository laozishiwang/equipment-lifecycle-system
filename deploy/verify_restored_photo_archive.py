#!/usr/bin/env python3
"""Check restored database photo names against a private-upload archive without extracting it."""
import json
import re
import sys
import tarfile
from collections import Counter

PHOTO_NAME=re.compile(r'[0-9a-f-]{36}\.(?:jpg|png)')

def inspect_archive(archive_path,references):
    names=set(references)
    if any(not PHOTO_NAME.fullmatch(name) for name in names):
        raise ValueError('Invalid stored photo name in restored database')
    with tarfile.open(archive_path,'r:gz') as archive:
        entries=list(archive)
        files=Counter(member.name for member in entries if member.isfile())
        all_entries=Counter(member.name for member in entries)
    missing=sorted(name for name in names if files['./'+name]==0)
    duplicates=sorted(name for name in names if all_entries['./'+name]>1)
    return {'referenced_count':len(names),'missing_count':len(missing),'duplicate_count':len(duplicates),
            'missing_examples':missing[:10],'duplicate_examples':duplicates[:10]}

def main():
    if len(sys.argv)!=2:
        print('Usage: verify_restored_photo_archive.py ARCHIVE < REFERENCES',file=sys.stderr)
        return 2
    try:
        result=inspect_archive(sys.argv[1],sys.stdin.read().splitlines())
    except (OSError,ValueError,tarfile.TarError) as error:
        print(json.dumps({'status':'error','message':str(error)}))
        return 2
    print(json.dumps(result))
    return 1 if result['missing_count'] or result['duplicate_count'] else 0

if __name__=='__main__':sys.exit(main())
