import json, os, subprocess, urllib.request
if os.environ.get("EMS_ISOLATED_FIXTURE")!="YES": raise SystemExit("isolated fixture required")
base="http://127.0.0.1:22090/prod-api"; opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
def db(sql): subprocess.run(["docker","exec","-i","scope-race-20261105-mysql-1","sh","-c",'mysql -uroot -p"$MYSQL_ROOT_PASSWORD" scope_test_race 2>/dev/null'],input=sql.encode(),check=True)
def req(path,token=None,body=None):
 r=urllib.request.Request(base+path,None if body is None else json.dumps(body).encode(),{"Content-Type":"application/json",**({"Authorization":"Bearer "+token} if token else {})})
 with opener.open(r,timeout=15) as x:return json.load(x)
def ids(t):
 r=req("/equipment/assets/departments",t); assert r.get("code")==200,r; return {x["dept_id"] for x in r["data"]}
db("UPDATE sys_role SET status='0',data_scope='3' WHERE role_id=99001; INSERT IGNORE INTO sys_role_menu SELECT 99001,menu_id FROM sys_menu WHERE perms='equipment:asset:edit';")
t=req("/login",body={"username":"race_reader","password":"admin123"})["token"]; admin=req("/login",body={"username":"admin","password":"admin123"})["token"]
if os.environ.get("EMS_EXPECT_DISABLED")=="YES":
 assert {99001,99002} <= ids(t)
 print("disabled scope compatibility passed")
else:
 assert 99001 in ids(t) and 99002 not in ids(t)
 assert {99001,99002} <= ids(admin)
 db("UPDATE sys_role SET data_scope='1' WHERE role_id=99001")
 assert {99001,99002} <= ids(t)
 db("UPDATE sys_role SET status='1' WHERE role_id=99001")
 assert not ids(t)
 print("department list own, cross, all, admin and revocation passed")
