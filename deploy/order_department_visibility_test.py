import json, os, subprocess, urllib.request, urllib.error
if os.environ.get("EMS_ISOLATED_FIXTURE")!="YES": raise SystemExit("isolated fixture required")
base="http://127.0.0.1:22090/prod-api"
opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
def db(sql):
 subprocess.run(["docker","exec","-i","scope-race-20261105-mysql-1","sh","-c",'mysql -uroot -p"$MYSQL_ROOT_PASSWORD" scope_test_race 2>/dev/null'],input=sql.encode(),check=True)
def req(path,token=None,body=None):
 r=urllib.request.Request(base+path, None if body is None else json.dumps(body).encode(), {"Content-Type":"application/json",**({"Authorization":"Bearer "+token} if token else {})})
 try:
  with opener.open(r,timeout=15) as x:
   data=x.read();return x.status,json.loads(data) if x.headers.get_content_type()=="application/json" else data
 except urllib.error.HTTPError as x:return x.code,None
def ok(result):return result[0]==200 and (not isinstance(result[1],dict) or result[1].get("code")==200)
db("UPDATE sys_role SET status='0' WHERE role_id=99001; INSERT IGNORE INTO sys_role_menu SELECT 99001,menu_id FROM sys_menu WHERE perms='equipment:order:list'; DELETE rm FROM sys_role_menu rm JOIN sys_menu m ON m.menu_id=rm.menu_id WHERE rm.role_id=99001 AND m.perms='equipment:order:viewAll'; UPDATE ems_equipment_department SET dept_id=99001 WHERE equipment_id=99001; UPDATE ems_work_order SET status='CLOSED',reporter_id=1,technician_id=1 WHERE id=99001;")
token=req("/login",body={"username":"race_reader","password":"admin123"})[1]["token"]
paths=["/equipment/orders/99001","/equipment/orders/99001/costs","/equipment/orders/99001/photos","/equipment/orders/photos/99001"]
assert all(ok(req(p,token)) for p in paths),"same department denied"
r=req("/equipment/orders",token);assert ok(r) and any(row["id"]==99001 for row in r[1]["data"]),"list missing same department"
db("UPDATE ems_equipment_department SET dept_id=99002 WHERE equipment_id=99001")
assert all(not ok(req(p,token)) for p in paths),"cross department leaked"
db("UPDATE ems_work_order SET reporter_id=99001 WHERE id=99001")
assert all(ok(req(p,token)) for p in paths),"participant denied"
db("UPDATE sys_role SET status='1' WHERE role_id=99001")
assert all(not ok(req(p,token)) for p in paths),"revoked role leaked"
print("same department, cross department, participant, revoked role passed")
