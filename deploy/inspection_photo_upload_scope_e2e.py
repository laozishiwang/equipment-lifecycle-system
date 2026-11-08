import base64,concurrent.futures,json,os,subprocess,time,urllib.request,urllib.error,uuid,pymysql
if os.environ.get('EMS_ISOLATED_FIXTURE')!='YES':raise SystemExit('isolated fixture required')
base='http://127.0.0.1:22090/prod-api';opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
def sql(q):
 return subprocess.run(['docker','exec','-i','scope-race-20261105-mysql-1','sh','-c','mysql -uroot -p"$MYSQL_ROOT_PASSWORD" scope_test_race -N 2>/dev/null'],input=q.encode(),stdout=subprocess.PIPE,check=True).stdout.decode().strip()
def request(path,token=None,body=None,content='application/json'):
 r=urllib.request.Request(base+path,body,{'Content-Type':content,**({'Authorization':'Bearer '+token} if token else {})})
 try:
  with opener.open(r,timeout=25) as x:return json.load(x)
 except urllib.error.HTTPError as e:return {'code':e.code}
def upload(i,t):
 b='boundary'+uuid.uuid4().hex;png=base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/6x0AAAAASUVORK5CYII='); data=('--'+b+'\r\nContent-Disposition: form-data; name="file"; filename="fixture.png"\r\nContent-Type: image/png\r\n\r\n').encode()+png+('\r\n--'+b+'--\r\n').encode();return request('/equipment/inspections/%d/photos'%i,t,data,'multipart/form-data; boundary='+b)
sql("UPDATE sys_role SET status='0',data_scope='3' WHERE role_id=99001; INSERT IGNORE INTO sys_role_menu SELECT 99001,menu_id FROM sys_menu WHERE perms IN ('equipment:inspection:list','equipment:inspection:add'); INSERT INTO ems_inspection(id,equipment_id,inspector_id,inspected_at,result) VALUES (99010,99001,1,NOW(),'NORMAL'); INSERT INTO ems_equipment(id,code,name) VALUES (99002,'PHOTO-B','Photo B'); INSERT INTO ems_equipment_department VALUES(99002,99002); INSERT INTO ems_inspection(id,equipment_id,inspector_id,inspected_at,result) VALUES (99011,99002,1,NOW(),'NORMAL');")
t=request('/login',body=json.dumps({'username':'race_reader','password':'admin123'}).encode())['token']
assert upload(99010,t)['code']==200,'same department must upload'
assert upload(99011,t)['code']!=200,'cross department must be denied'
for permission in ('equipment:inspection:list','equipment:inspection:add'):
 sql("DELETE rm FROM sys_role_menu rm JOIN sys_menu m ON m.menu_id=rm.menu_id WHERE rm.role_id=99001 AND m.perms='"+permission+"'")
 assert upload(99010,t)['code']!=200,'revoked action must be denied'
 sql("INSERT IGNORE INTO sys_role_menu SELECT 99001,menu_id FROM sys_menu WHERE perms='"+permission+"'")
db=pymysql.connect(host='127.0.0.1',port=23306,user='scope_race',password='isolated-race-only-43',database='scope_test_race',autocommit=True);monitor=pymysql.connect(host='127.0.0.1',port=23306,user='scope_race',password='isolated-race-only-43',database='scope_test_race',autocommit=True)
try:
 db.begin()
 with db.cursor() as c:c.execute('SELECT id FROM ems_equipment WHERE id=99001 FOR UPDATE');c.execute('UPDATE ems_equipment_department SET dept_id=99002 WHERE equipment_id=99001')
 with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
  f=pool.submit(upload,99010,t);deadline=time.monotonic()+10;waiting=False
  while time.monotonic()<deadline:
   with monitor.cursor() as c:
    c.execute("SELECT COUNT(*) FROM performance_schema.data_lock_waits w JOIN performance_schema.data_locks l ON l.ENGINE_LOCK_ID=w.BLOCKING_ENGINE_LOCK_ID WHERE l.OBJECT_SCHEMA='scope_test_race' AND l.OBJECT_NAME='ems_equipment'")
    if c.fetchone()[0]:waiting=True;break
   time.sleep(.05)
  if not waiting:db.rollback();raise AssertionError('no equipment lock wait')
  db.commit();assert f.result()['code']!=200,'transfer race must deny'
 print('inspection photo same department, cross department, action revocation and transfer race passed')
finally:db.rollback();db.close();monitor.close()
