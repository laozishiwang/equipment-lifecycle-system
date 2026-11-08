#!/usr/bin/env python3
"""Read-only, best-effort audit of private photo storage in a Compose deployment."""
import argparse
import json
import re
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PHOTO_NAME = re.compile(r'[0-9a-f-]{36}\.(?:jpg|png)')


def parse_df(output):
    lines=output.strip().splitlines()
    if len(lines)!=2:
        raise ValueError('Unable to parse df output')
    columns=lines[1].split()
    if len(columns)<6 or not re.fullmatch(r'\d+%',columns[-2]):
        raise ValueError('Unable to parse df usage')
    value=int(columns[-2][:-1])
    if not 0<=value<=100:
        raise ValueError('Invalid df usage')
    return value


def parse_storage_sizes(output):
    total=0
    for item in output.split(b'\0'):
        if not item:
            continue
        if not re.fullmatch(rb'\d+',item):
            raise ValueError('Invalid private storage file size')
        total+=int(item)
    return total


def quota_warning(used, limit, warning_percent):
    if used < 0 or limit <= 0:
        raise ValueError('Invalid private storage quota')
    return used * 100 >= limit * warning_percent


def audit_state(references, files, now, grace_seconds):
    missing=sorted(references-files.keys())
    unreferenced=files.keys()-references
    old=sorted(name for name in unreferenced if files[name]<=now-grace_seconds)
    return {'missing':missing,'orphan_candidates':old,'recent_unreferenced':len(unreferenced)-len(old)}


def execute(compose, service, command):
    try:
        result=subprocess.run(compose+['exec','-T',service]+command,cwd=ROOT,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=120,check=True)
        return result.stdout
    except (OSError, subprocess.SubprocessError) as exc:
        raise RuntimeError('Unable to read '+service+'; verify Compose services, permissions, and database access') from exc


def audit(args):
    compose=['docker','compose','--project-name',args.project,'--env-file',args.env_file,'-f',args.compose_file]
    query='SELECT stored_name FROM ems_work_order_photo UNION SELECT stored_name FROM ems_inspection_photo UNION SELECT stored_name FROM ems_inspection_photo_stage'
    raw=execute(compose,'mysql',['sh','-c','exec mysql --default-character-set=utf8mb4 -N -B -u"$MYSQL_USER" -p"$MYSQL_PASSWORD" "$MYSQL_DATABASE" -e "$1"','audit',query])
    refs=set(raw.decode('utf-8').splitlines())
    if any(not PHOTO_NAME.fullmatch(name) for name in refs):
        raise ValueError('Database contains an unexpected photo name; audit stopped')
    listing=execute(compose,'backend',['find','/app/private-uploads','-maxdepth','1','-type','f','-printf',r'%T@\t%f\0'])
    files={}
    unexpected=0
    for item in listing.split(b'\0'):
        if not item:continue
        parts=item.split(b'\t',1)
        if len(parts)!=2:raise ValueError('Invalid file listing')
        name=parts[1].decode('utf-8',errors='replace')
        if not PHOTO_NAME.fullmatch(name):
            unexpected+=1
            continue
        files[name]=float(parts[0].decode('ascii'))
    disk=parse_df(execute(compose,'backend',['df','-Pk','/app/private-uploads']).decode('utf-8'))
    inode=parse_df(execute(compose,'backend',['df','-Pi','/app/private-uploads']).decode('utf-8'))
    sizes=execute(compose,'backend',['find','/app/private-uploads','-type','f','-printf',r'%s\0'])
    used_bytes=parse_storage_sizes(sizes)
    raw_limit=execute(compose,'backend',['printenv','EMS_PRIVATE_UPLOAD_MAX_BYTES']).decode('ascii').strip()
    if not re.fullmatch(r'\d+',raw_limit):
        raise ValueError('Invalid private storage limit configuration')
    limit_bytes=int(raw_limit)
    quota_alert=quota_warning(used_bytes,limit_bytes,args.warning_percent)
    findings=audit_state(refs,files,time.time(),args.grace_hours*3600)
    warning=quota_alert or disk>=args.warning_percent or inode>=args.warning_percent or bool(findings['missing']) or bool(findings['orphan_candidates']) or unexpected>0
    return {'status':'warning' if warning else 'ok','filesystem_used_percent':disk,'inode_used_percent':inode,
            'warning_percent':args.warning_percent,'referenced_names':len(refs),'photo_files':len(files),
            'private_used_bytes':used_bytes,'private_limit_bytes':limit_bytes,'private_quota_warning':quota_alert,
            'missing_count':len(findings['missing']),'missing_examples':findings['missing'][:20],
            'orphan_candidate_count':len(findings['orphan_candidates']),'orphan_candidate_examples':findings['orphan_candidates'][:20],
            'recent_unreferenced_count':findings['recent_unreferenced'],'unexpected_files':unexpected,
            'grace_hours':args.grace_hours,
            'notice':'Read-only, non-atomic snapshot; verify findings against a current backup and database before any action.'}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--project',default='equipment')
    p.add_argument('--compose-file',default='compose.production.yaml')
    p.add_argument('--env-file',default='.env.production')
    p.add_argument('--grace-hours',type=int,default=24)
    p.add_argument('--warning-percent',type=int,default=85)
    args=p.parse_args()
    if args.grace_hours<24 or not 1<=args.warning_percent<=100:
        p.error('grace-hours must be >= 24 and warning-percent must be 1..100')
    try:
        report=audit(args)
    except (RuntimeError, ValueError, UnicodeError) as exc:
        print(json.dumps({'status':'error','message':str(exc)},ensure_ascii=False))
        return 2
    print(json.dumps(report,ensure_ascii=False,indent=2))
    return 1 if report['status']=='warning' else 0

if __name__=='__main__':sys.exit(main())
