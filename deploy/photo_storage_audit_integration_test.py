#!/usr/bin/env python3
"""Run only against the equipment-rebuild isolated development project."""
import json
import subprocess
import uuid

name=str(uuid.uuid4())+'.png'
path='/app/private-uploads/'+name
base=['docker','exec','equipment-rebuild-backend-1']
created=False
try:
    subprocess.run(base+['sh','-c','set -C; umask 077; : > "$1"; touch -d "48 hours ago" "$1"','fixture',path],check=True)
    created=True
    command=['python3','deploy/photo_storage_audit.py','--project','equipment-rebuild','--compose-file','compose.dev.yaml','--env-file','.env']
    result=subprocess.run(command,capture_output=True,text=True,timeout=180)
    assert result.returncode==1,(result.returncode,result.stdout,result.stderr)
    report=json.loads(result.stdout)
    assert report['orphan_candidate_count']>=1 and name in report['orphan_candidate_examples'],report
    subprocess.run(base+['test','-f',path],check=True)
    threshold=subprocess.run(command+['--warning-percent','1'],capture_output=True,text=True,timeout=180)
    assert threshold.returncode==1 and json.loads(threshold.stdout)['status']=='warning'
    print('read-only orphan detection, file preservation and capacity warning passed')
finally:
    if created:subprocess.run(base+['rm','--',path],check=True)
