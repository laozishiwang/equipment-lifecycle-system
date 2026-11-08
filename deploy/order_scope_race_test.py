#!/usr/bin/env python3
"""Disposable isolated fixtures only. Requires PyMySQL and two valid isolated bearer tokens.

The order must be visible to the reader in OLD_DEPT, assigned to neither the reader
nor a technician with pending access, and become inaccessible after NEW_DEPT is set.
The fixture must include a photo; the reader must have both list and photo access.
Uses MySQL data_lock_waits to observe a real lock wait before committing the change.
Run only with experimental scope enabled in a separate isolated test deployment.
"""
import concurrent.futures
import json
import os
import time
import urllib.error
import urllib.request
import pymysql

if os.environ.get('EMS_ISOLATED_FIXTURE') != 'YES':
    raise SystemExit('Refusing: set EMS_ISOLATED_FIXTURE=YES for disposable isolation')
if any(os.environ.get(k) for k in ('HTTP_PROXY','HTTPS_PROXY','ALL_PROXY','BASE_URL','EMS_BASE_URL')):
    raise SystemExit('Refusing proxies and configurable HTTP targets')

def req(name):
    v=os.environ.get(name)
    if not v: raise SystemExit('Missing '+name)
    return v

# Explicit TCP loopback: never allow network targets or production database names.
port=int(req('EMS_TEST_MYSQL_PORT'))
if port in (3306,443,80) or not (1024 <= port <= 65535): raise SystemExit('Unsafe database port')
database=req('EMS_TEST_MYSQL_DATABASE')
if not database.startswith('scope_test_'): raise SystemExit('Database name must start scope_test_')
equipment=int(req('EMS_TEST_EQUIPMENT_ID')); order=int(req('EMS_TEST_ORDER_ID'))
photo=int(req('EMS_TEST_PHOTO_ID')); old=int(req('EMS_TEST_OLD_DEPT')); new=int(req('EMS_TEST_NEW_DEPT'))
if min(equipment,order,photo,old,new)<=0 or old==new: raise SystemExit('Invalid fixture identifiers')
http_port=int(req('EMS_TEST_HTTP_PORT'))
if not 20000 <= http_port <= 29999: raise SystemExit('HTTP port must be dedicated 20000-29999')
token=req('EMS_TEST_READER_TOKEN')
db=pymysql.connect(host='127.0.0.1',port=port,user=req('EMS_TEST_MYSQL_USER'),password=req('EMS_TEST_MYSQL_PASSWORD'),database=database,autocommit=True,connect_timeout=5)
monitor=pymysql.connect(host='127.0.0.1',port=port,user=req('EMS_TEST_MYSQL_USER'),password=req('EMS_TEST_MYSQL_PASSWORD'),database=database,autocommit=True,connect_timeout=5)
opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
def get(path):
    request=urllib.request.Request('http://127.0.0.1:%d/prod-api'%http_port+path,headers={'Authorization':'Bearer '+token})
    try:
        with opener.open(request,timeout=20) as response:
            data=response.read(); kind=response.headers.get_content_type()
            return response.status, json.loads(data) if kind=='application/json' else data
    except urllib.error.HTTPError as ex: return ex.code, None

def allowed(result):
    status,body=result
    return status==200 and (not isinstance(body,dict) or body.get('code')==200)

def wait_for_lock():
    deadline=time.monotonic()+10
    while time.monotonic()<deadline:
        with monitor.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM performance_schema.data_lock_waits w JOIN performance_schema.data_locks l ON l.ENGINE_LOCK_ID=w.BLOCKING_ENGINE_LOCK_ID WHERE l.OBJECT_SCHEMA=%s AND l.OBJECT_NAME='ems_equipment'",(database,))
            if cur.fetchone()[0]>0: return
        time.sleep(.05)
    raise AssertionError('No database lock wait observed; test cannot prove serialization')

try:
    with db.cursor() as cur:
        cur.execute('SELECT equipment_id,status FROM ems_work_order WHERE id=%s',(order,)); row=cur.fetchone()
        if not row or row[0]!=equipment or row[1]=='REPORTED': raise SystemExit('Order fixture mismatch or pending')
        cur.execute('SELECT work_order_id FROM ems_work_order_photo WHERE id=%s',(photo,)); row=cur.fetchone()
        if not row or row[0]!=order: raise SystemExit('Photo fixture mismatch')
        cur.execute('SELECT dept_id FROM ems_equipment_department WHERE equipment_id=%s',(equipment,)); row=cur.fetchone()
        if not row or row[0]!=old: raise SystemExit('Old department mismatch')
    for path in ('/equipment/orders/%d'%order,'/equipment/orders/%d/costs'%order,'/equipment/orders/photos/%d'%photo):
        if not allowed(get(path)): raise AssertionError('Fixture not initially visible: '+path)
        db.begin()
        with db.cursor() as cur:
            cur.execute('SELECT id FROM ems_equipment WHERE id=%s FOR UPDATE',(equipment,))
            cur.execute('UPDATE ems_equipment_department SET dept_id=%s WHERE equipment_id=%s',(new,equipment))
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            future=pool.submit(get,path)
            try: wait_for_lock()
            except BaseException:
                db.rollback(); raise
            db.commit()
            if allowed(future.result()): raise AssertionError('Reader retained access after committed transfer: '+path)
        # Restore solely inside this isolated disposable database.
        with db.cursor() as cur: cur.execute('UPDATE ems_equipment_department SET dept_id=%s WHERE equipment_id=%s',(old,equipment))
    print('isolated order detail, cost, photo ownership races passed')
finally:
    db.rollback(); db.close(); monitor.close()
