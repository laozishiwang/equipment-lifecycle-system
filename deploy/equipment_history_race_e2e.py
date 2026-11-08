import concurrent.futures,json,os,time,urllib.request,pymysql
if os.environ.get('EMS_ISOLATED_FIXTURE')!='YES':raise SystemExit('isolated fixture required')
base='http://127.0.0.1:22090/prod-api';opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
db=pymysql.connect(host='127.0.0.1',port=23306,user='scope_race',password='isolated-race-only-43',database='scope_test_race',autocommit=True)
mon=pymysql.connect(host='127.0.0.1',port=23306,user='scope_race',password='isolated-race-only-43',database='scope_test_race',autocommit=True)
def req(path,t=None,body=None):
 r=urllib.request.Request(base+path,None if body is None else json.dumps(body).encode(),{'Content-Type':'application/json',**({'Authorization':'Bearer '+t} if t else {})})
 with opener.open(r,timeout=20) as x:return json.load(x)
try:
 with db.cursor() as c:
  c.execute("UPDATE sys_role SET status='0',data_scope='3' WHERE role_id=99001")
  c.execute("INSERT IGNORE INTO sys_role_menu SELECT 99001,menu_id FROM sys_menu WHERE perms='equipment:asset:history'")
  c.execute('UPDATE ems_equipment_department SET dept_id=99001 WHERE equipment_id=99001')
 token=req('/login',body={'username':'race_reader','password':'admin123'})['token']
 assert req('/equipment/assets/99001/history',token)['code']==200
 db.begin()
 with db.cursor() as c:
  c.execute('SELECT id FROM ems_equipment WHERE id=99001 FOR UPDATE')
  c.execute('UPDATE ems_equipment_department SET dept_id=99002 WHERE equipment_id=99001')
 with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
  future=pool.submit(req,'/equipment/assets/99001/history',token)
  deadline=time.monotonic()+10; observed=False
  while time.monotonic()<deadline:
   with mon.cursor() as c:
    c.execute("SELECT COUNT(*) FROM performance_schema.data_lock_waits w JOIN performance_schema.data_locks l ON l.ENGINE_LOCK_ID=w.BLOCKING_ENGINE_LOCK_ID WHERE l.OBJECT_SCHEMA='scope_test_race' AND l.OBJECT_NAME='ems_equipment'")
    if c.fetchone()[0]:observed=True;break
   time.sleep(.05)
  if not observed:db.rollback();raise AssertionError('no actual lock wait')
  db.commit();assert future.result()['code']!=200
 print('equipment history transfer race denied after committed scope change')
finally:db.rollback();db.close();mon.close()
