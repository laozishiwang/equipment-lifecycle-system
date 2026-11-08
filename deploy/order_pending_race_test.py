#!/usr/bin/env python3
"""Only for scope-race-20261105 disposable deployment; never use shared databases."""
import concurrent.futures,json,os,time,urllib.error,urllib.request
import pymysql
if os.environ.get('EMS_ISOLATED_FIXTURE')!='YES': raise SystemExit('Refusing without isolated fixture')
for k in ('HTTP_PROXY','HTTPS_PROXY','ALL_PROXY','http_proxy','https_proxy','all_proxy'): os.environ.pop(k,None)
db=pymysql.connect(host='127.0.0.1',port=23306,user='scope_race',password='isolated-race-only-43',database='scope_test_race',autocommit=True)
monitor=pymysql.connect(host='127.0.0.1',port=23306,user='scope_race',password='isolated-race-only-43',database='scope_test_race',autocommit=True)
try:
 with db.cursor() as c:
  c.execute("INSERT IGNORE INTO sys_role(role_id,role_name,role_key,role_sort,data_scope,status,del_flag) VALUES (99002,'Race technician','race_tech',1,'3','0','0')")
  c.execute("INSERT IGNORE INTO sys_user(user_id,dept_id,user_name,nick_name,password,status,del_flag) SELECT 99002,99001,'race_tech','Race tech',password,'0','0' FROM sys_user WHERE user_id=1")
  c.execute('INSERT IGNORE INTO sys_user_role(user_id,role_id) VALUES (99002,99002)')
  c.execute("INSERT IGNORE INTO sys_role_menu(role_id,menu_id) SELECT 99002,menu_id FROM sys_menu WHERE perms IN ('equipment:order:list','equipment:order:accept')")
  c.execute('UPDATE ems_equipment_department SET dept_id=99002 WHERE equipment_id=99001')
  c.execute("UPDATE ems_work_order SET status='REPORTED',reporter_id=1,technician_id=NULL WHERE id=99001")
 opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
 token=None
 for _ in range(60):
  try:
   req=urllib.request.Request('http://127.0.0.1:22090/prod-api/login',json.dumps({'username':'race_tech','password':'admin123'}).encode(),{'Content-Type':'application/json'})
   with opener.open(req,timeout=5) as r: token=json.load(r).get('token')
   if token: break
  except Exception: pass
  time.sleep(2)
 if not token: raise AssertionError('isolated login unavailable')
 def get(path):
  req=urllib.request.Request('http://127.0.0.1:22090/prod-api'+path,headers={'Authorization':'Bearer '+token})
  try:
   with opener.open(req,timeout=20) as r:
    data=r.read(); return r.status,json.loads(data) if r.headers.get_content_type()=='application/json' else data
  except urllib.error.HTTPError as e: return e.code,None
 def allowed(result): return result[0]==200 and (not isinstance(result[1],dict) or result[1].get('code')==200)
 def wait():
  deadline=time.monotonic()+10
  while time.monotonic()<deadline:
   with monitor.cursor() as c:
    c.execute("SELECT COUNT(*) FROM performance_schema.data_lock_waits w JOIN performance_schema.data_locks l ON l.ENGINE_LOCK_ID=w.BLOCKING_ENGINE_LOCK_ID WHERE l.OBJECT_SCHEMA='scope_test_race' AND l.OBJECT_NAME='ems_equipment'")
    if c.fetchone()[0]: return
   time.sleep(.05)
  raise AssertionError('No equipment row lock wait observed')
 for path in ['/equipment/orders/99001','/equipment/orders/photos/99001']:
  with db.cursor() as c: c.execute("UPDATE ems_work_order SET status='REPORTED',technician_id=NULL WHERE id=99001")
  if not allowed(get(path)): raise AssertionError('pending order initially invisible: '+path)
  db.begin()
  with db.cursor() as c:
   c.execute('SELECT id FROM ems_equipment WHERE id=99001 FOR UPDATE')
   c.execute("UPDATE ems_work_order SET status='ACCEPTED',technician_id=1 WHERE id=99001")
  with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
   f=pool.submit(get,path)
   try: wait()
   except BaseException: db.rollback(); raise
   db.commit()
   if allowed(f.result()): raise AssertionError('access retained after acceptance: '+path)
 with db.cursor() as c:
  c.execute("UPDATE ems_work_order SET status='REPORTED',technician_id=NULL WHERE id=99001")
 if not allowed(get('/equipment/orders/99001')): raise AssertionError('fixture should be visible before revoke')
 with db.cursor() as c: c.execute("DELETE rm FROM sys_role_menu rm JOIN sys_menu m ON m.menu_id=rm.menu_id WHERE rm.role_id=99002 AND m.perms='equipment:order:accept'")
 for path in ['/equipment/orders/99001','/equipment/orders/photos/99001']:
  if allowed(get(path)): raise AssertionError('old token retained revoked pending access: '+path)
 print('isolated pending acceptance race and old-token revocation passed')
finally:
 db.rollback(); db.close(); monitor.close()
