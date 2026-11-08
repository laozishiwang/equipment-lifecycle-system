#!/usr/bin/env python3
"""Exercise a full backup and disposable restore using synthetic data in isolation only."""
import base64
import gzip
import hashlib
import json
import os
import re
import subprocess
import tarfile
import time
import urllib.request
import uuid
from pathlib import Path
from verify_restored_photo_archive import inspect_archive

ROOT=Path(__file__).resolve().parent.parent
BASE='http://127.0.0.1:18090/prod-api'
PNG=base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/6x0AAAAASUVORK5CYII=')
NAME=re.compile(r'[0-9a-f-]{36}\.(?:jpg|png)')

def call(path,method='GET',data=None,token=None,content_type='application/json'):
    headers={'Content-Type':content_type}
    if token: headers['Authorization']='Bearer '+token
    request=urllib.request.Request(BASE+path,data,headers,method=method)
    with urllib.request.urlopen(request,timeout=30) as response:return json.load(response)

def post(path,value,token=None):
    return call(path,'POST',json.dumps(value).encode(),token)

def upload(path,token):
    boundary='test'+uuid.uuid4().hex
    body=('--'+boundary+'\r\nContent-Disposition: form-data; name="file"; filename="fixture.png"\r\nContent-Type: image/png\r\n\r\n').encode()+PNG
    body+=('\r\n--'+boundary+'--\r\n').encode()
    result=call(path,'POST',body,token,'multipart/form-data; boundary='+boundary)
    assert result.get('code')==200, result

def run(*args,**kwargs):
    kwargs.setdefault('cwd',ROOT)
    return subprocess.run(args,check=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE,**kwargs)

worker=post('/login',{'username':'role_worker_test','password':'admin123'})['token']
tag='restore-fixture-'+uuid.uuid4().hex[:12]
order=post('/equipment/orders',{'equipmentId':1,'description':tag},worker)['data']['id']
inspection=post('/equipment/inspections',{'equipmentId':1,'result':'NORMAL','remark':tag},worker)['data']['inspectionId']
upload(f'/equipment/orders/{order}/photos',worker)
upload(f'/equipment/inspections/{inspection}/photos',worker)

env=os.environ.copy()
env.update(COMPOSE_PROJECT_NAME='equipment-rebuild',COMPOSE_FILE='compose.dev.yaml',ENV_FILE='.env',BACKUP_ROOT='/opt/equipment-rebuild/backups/full-restore-rehearsal')
output=run('bash','deploy/backup.sh',env=env,text=True).stdout
match=re.search(r'^Backup created: (.+)$',output,re.MULTILINE)
assert match, 'Backup did not report its output directory'
backup=Path(match.group(1)).resolve(strict=True)
assert backup.parent==Path('/opt/equipment-rebuild/backups/full-restore-rehearsal')
run('sha256sum','-c','SHA256SUMS',cwd=backup)

container='equipment-dev-restore-'+uuid.uuid4().hex[:12]
created=False
try:
    run('docker','run','-d','--name',container,'--network','none','--memory=384m','--cpus=0.5',
        '--tmpfs','/var/lib/mysql:rw,size=256m','-e','MYSQL_ROOT_PASSWORD=isolated-restore-only',
        '-e','MYSQL_DATABASE=equipment','mysql:8.0','--innodb-buffer-pool-size=64M',
        '--performance-schema=OFF','--max-connections=10')
    created=True
    for _ in range(120):
        result=subprocess.run(['docker','exec',container,'mysqladmin','ping','-h','127.0.0.1','-uroot','-pisolated-restore-only','--silent'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        if result.returncode==0: break
        time.sleep(1)
    else: raise RuntimeError('Disposable restore database did not become ready')
    with gzip.open(backup/'database.sql.gz','rb') as dump:
        run('docker','exec','-i',container,'mysql','-uroot','-pisolated-restore-only','equipment',input=dump.read())
    query=(f"SELECT stored_name FROM ems_work_order_photo WHERE work_order_id={int(order)} UNION ALL "
           f"SELECT stored_name FROM ems_inspection_photo WHERE inspection_id={int(inspection)};")
    names=run('docker','exec',container,'mysql','-N','-B','-uroot','-pisolated-restore-only','equipment','-e',query,text=True).stdout.splitlines()
    assert len(names)==2 and all(NAME.fullmatch(name) for name in names),names
    all_query=('SELECT stored_name FROM ems_work_order_photo UNION SELECT stored_name FROM ems_inspection_photo '
               'UNION SELECT stored_name FROM ems_inspection_photo_stage')
    references=run('docker','exec',container,'mysql','-N','-B','-uroot','-pisolated-restore-only','equipment','-e',all_query,text=True).stdout.splitlines()
    assert all(NAME.fullmatch(name) for name in references), 'Unexpected stored photo name in restored database'
    report=inspect_archive(backup/'private-uploads.tar.gz',references)
    assert report['missing_count']==0 and report['duplicate_count']==0,report
    expected=hashlib.sha256(PNG).digest()
    with tarfile.open(backup/'private-uploads.tar.gz','r:gz') as archive:
        for name in names:
            member=archive.getmember('./'+name)
            assert member.isfile() and member.size==len(PNG)
            with archive.extractfile(member) as stream: assert hashlib.sha256(stream.read()).digest()==expected
    print('restored database references both synthetic photos; archive contents match SHA-256')
    print('restored private photo references verified:',len(references))
    print('backup:',backup)
finally:
    if created: subprocess.run(['docker','rm','-f',container],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
