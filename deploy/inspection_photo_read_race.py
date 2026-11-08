import concurrent.futures,json,os,time,urllib.request,urllib.error,pymysql
if os.environ.get("EMS_ISOLATED_FIXTURE")!="YES": raise SystemExit("isolated fixture required")
db=pymysql.connect(host="127.0.0.1",port=23307,user="scope_race",password="isolated-race-only-43",database="scope_test_race",autocommit=True)
mon=pymysql.connect(host="127.0.0.1",port=23307,user="scope_race",password="isolated-race-only-43",database="scope_test_race",autocommit=True)
opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
def get(token):
 r=urllib.request.Request("http://127.0.0.1:22091/prod-api/equipment/inspections/photos/99001",headers={"Authorization":"Bearer "+token})
 try:
  with opener.open(r,timeout=20) as x:return x.status
 except urllib.error.HTTPError as e:return e.code
try:
 req=urllib.request.Request("http://127.0.0.1:22091/prod-api/login",json.dumps({"username":"race_reader","password":"admin123"}).encode(),{"Content-Type":"application/json"})
 with opener.open(req,timeout=15) as r: token=json.load(r)["token"]
 assert get(token)==200,"same-department reader cannot read another user's photo"
 db.begin()
 with db.cursor() as c:
  c.execute("SELECT id FROM ems_equipment WHERE id=99001 FOR UPDATE")
  c.execute("UPDATE ems_equipment_department SET dept_id=99002 WHERE equipment_id=99001")
 with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
  f=pool.submit(get,token); deadline=time.monotonic()+10
  while time.monotonic()<deadline:
   with mon.cursor() as c:
    c.execute("SELECT COUNT(*) FROM performance_schema.data_lock_waits w JOIN performance_schema.data_locks l ON l.ENGINE_LOCK_ID=w.BLOCKING_ENGINE_LOCK_ID WHERE l.OBJECT_SCHEMA='scope_test_race' AND l.OBJECT_NAME='ems_equipment'")
    if c.fetchone()[0]:break
   time.sleep(.05)
  else: db.rollback(); raise AssertionError("no lock wait observed")
  db.commit(); assert f.result()!=200,"photo leaked after department transfer"
 print("inspection photo same-department and transfer race passed")
finally:
 db.rollback()
 with db.cursor() as c:c.execute("UPDATE ems_equipment_department SET dept_id=99001 WHERE equipment_id=99001")
 db.close();mon.close()
