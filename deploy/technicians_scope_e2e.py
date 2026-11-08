import json,os,subprocess,urllib.request
if os.getenv("EMS_ISOLATED_FIXTURE")!="YES":raise SystemExit("isolated fixture required")
def db(s):subprocess.run(["docker","exec","-i","scope-race-20261105-mysql-1","sh","-c",'mysql -uroot -p"$MYSQL_ROOT_PASSWORD" scope_test_race 2>/dev/null'],input=s.encode(),check=True)
opener=urllib.request.build_opener(urllib.request.ProxyHandler({}));base="http://127.0.0.1:22090/prod-api"
def call(path,token=None,body=None):
 req=urllib.request.Request(base+path,None if body is None else json.dumps(body).encode(),{"Content-Type":"application/json",**({"Authorization":"Bearer "+token} if token else {})})
 with opener.open(req,timeout=20) as r:return json.load(r)
restore="INSERT IGNORE INTO sys_role_menu SELECT 99001,menu_id FROM sys_menu WHERE perms='equipment:order:assign'"
try:
 db("UPDATE sys_role SET status='0' WHERE role_id=99001; "+restore)
 token=call('/login',body={'username':'race_reader','password':'admin123'})['token']
 assert call('/equipment/orders/technicians',token)['code']==200
 db("DELETE rm FROM sys_role_menu rm JOIN sys_menu m ON m.menu_id=rm.menu_id WHERE rm.role_id=99001 AND m.perms='equipment:order:assign'")
 assert call('/equipment/orders/technicians',token)['code']!=200,'revoked token can still list technicians'
 print('technician listing rejects revoked assign permission with old token')
finally:db(restore)
