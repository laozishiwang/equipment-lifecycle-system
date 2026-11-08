import json,os,subprocess,urllib.request
if os.environ.get("EMS_ISOLATED_FIXTURE")!="YES":raise SystemExit("isolated fixture required")
base="http://127.0.0.1:22090/prod-api";opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
def db(s):subprocess.run(["docker","exec","-i","scope-race-20261105-mysql-1","sh","-c",'mysql -uroot -p"$MYSQL_ROOT_PASSWORD" scope_test_race 2>/dev/null'],input=s.encode(),check=True)
def req(path,token=None,body=None):
 r=urllib.request.Request(base+path,None if body is None else json.dumps(body).encode(),{"Content-Type":"application/json",**({"Authorization":"Bearer "+token} if token else {})})
 with opener.open(r,timeout=15) as x:return json.load(x)
db("UPDATE sys_role SET status='0',data_scope='3' WHERE role_id=99001; INSERT IGNORE INTO sys_role_menu SELECT 99001,menu_id FROM sys_menu WHERE perms IN ('equipment:asset:history','equipment:order:list','equipment:inspection:list'); UPDATE ems_equipment_department SET dept_id=99001 WHERE equipment_id=99001; INSERT IGNORE INTO ems_inspection(id,equipment_id,inspector_id,inspected_at,result,remark) VALUES(99010,99001,1,NOW(),'NORMAL','history'); UPDATE ems_work_order SET equipment_id=99001,reporter_id=1,technician_id=1,status='CLOSED' WHERE id=99001;")
t=req('/login',body={'username':'race_reader','password':'admin123'})['token']
if os.environ.get('EMS_EXPECT_DISABLED')=='YES':
 db('UPDATE ems_equipment_department SET dept_id=99002 WHERE equipment_id=99001')
 assert req('/equipment/assets/99001/history',t)['code']==200
 print('scope-disabled equipment history compatibility passed'); raise SystemExit(0)
r=req('/equipment/assets/99001/history',t);assert r['code']==200,r
assert any(x['id']==99010 for x in r['data']['inspections']) and any(x['id']==99001 for x in r['data']['orders']),r
db("DELETE rm FROM sys_role_menu rm JOIN sys_menu m ON m.menu_id=rm.menu_id WHERE rm.role_id=99001 AND m.perms IN ('equipment:order:list','equipment:inspection:list')")
r=req('/equipment/assets/99001/history',t);assert r['code']==200 and not r['data']['inspections'] and not r['data']['orders'],r
db('UPDATE ems_equipment_department SET dept_id=99002 WHERE equipment_id=99001')
assert req('/equipment/assets/99001/history',t)['code']!=200
print('scoped equipment history own department, child permission revocation, cross department passed')
