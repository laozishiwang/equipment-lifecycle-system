import json,os,subprocess,urllib.request,uuid
if os.environ.get("EMS_ISOLATED_FIXTURE")!="YES":raise SystemExit("isolated fixture required")
base="http://127.0.0.1:22090/prod-api";opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
def db(sql):
 return subprocess.run(["docker","exec","-i","scope-race-20261105-mysql-1","sh","-c",'mysql -uroot -p"$MYSQL_ROOT_PASSWORD" scope_test_race -N 2>/dev/null'],input=sql.encode(),check=True,stdout=subprocess.PIPE).stdout.decode().strip()
def req(path,t=None,body=None):
 r=urllib.request.Request(base+path,None if body is None else json.dumps(body).encode(),{"Content-Type":"application/json",**({"Authorization":"Bearer "+t} if t else {})})
 with opener.open(r,timeout=15) as x:return json.load(x)
db("UPDATE sys_role SET status='0',data_scope='3' WHERE role_id=99001; INSERT IGNORE INTO sys_role_menu SELECT 99001,menu_id FROM sys_menu WHERE perms='equipment:asset:add'; DELETE rm FROM sys_role_menu rm JOIN sys_menu m ON m.menu_id=rm.menu_id WHERE rm.role_id=99001 AND m.perms='equipment:asset:edit'")
t=req('/login',body={'username':'race_reader','password':'admin123'})['token'];a=req('/login',body={'username':'admin','password':'admin123'})['token']
opts=req('/equipment/assets/create-departments',t);assert opts['code']==200,opts
code='CREATE-'+uuid.uuid4().hex[:12]
if os.environ.get('EMS_EXPECT_DISABLED')=='YES':
 assert not opts['data']['required']
 assert req('/equipment/assets',t,{'code':code,'name':'isolated'})['code']==200
 print('disabled asset creation compatibility passed');raise SystemExit(0)
assert opts['data']['required'] and {x['dept_id'] for x in opts['data']['departments']}=={99001},opts
for dept in (None,99002,-1):
 r=req('/equipment/assets',t,{'code':code,'name':'isolated','deptId':dept});assert r['code']!=200,r
 assert db("SELECT COUNT(*) FROM ems_equipment WHERE code='"+code+"'")=='0'
r=req('/equipment/assets',t,{'code':code,'name':'isolated','deptId':99001});assert r['code']==200,r
assert db("SELECT COUNT(*) FROM ems_equipment e JOIN ems_equipment_department d ON d.equipment_id=e.id JOIN ems_equipment_department_history h ON h.equipment_id=e.id WHERE e.code='"+code+"' AND d.dept_id=99001 AND h.new_dept_id=99001")=='1'
assert req('/equipment/assets',a,{'code':code+'A','name':'admin'})['code']==200
failure=code+'F'
db("CREATE TRIGGER fail_create_history BEFORE INSERT ON ems_equipment_department_history FOR EACH ROW SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='isolated failure'")
try:
 try: result=req('/equipment/assets',t,{'code':failure,'name':'rollback','deptId':99001})
 except Exception: result={'code':500}
 assert result.get('code')!=200,result
 assert db("SELECT COUNT(*) FROM ems_equipment WHERE code='"+failure+"'")=='0'
finally: db('DROP TRIGGER fail_create_history')
print('scoped add-only asset creation, denial and atomic department history passed')
