import json,os,subprocess,urllib.request,urllib.error
if os.environ.get('EMS_ISOLATED_FIXTURE')!='YES': raise SystemExit('isolated fixture required')
def db(s): subprocess.run(['docker','exec','-i','scope-asset-edit-20261106-mysql-1','sh','-c','mysql -uroot -p"$MYSQL_ROOT_PASSWORD" scope_test_race 2>/dev/null'],input=s.encode(),check=True)
def req(path,token=None,body=None,method=None):
 r=urllib.request.Request('http://127.0.0.1:22193/prod-api'+path,None if body is None else json.dumps(body).encode(),{'Content-Type':'application/json',**({'Authorization':'Bearer '+token} if token else {})},method=method)
 try:
  with urllib.request.urlopen(r,timeout=15) as x:return json.load(x)
 except urllib.error.HTTPError as e:return {'code':e.code}
db("UPDATE sys_role SET status='0',data_scope='3' WHERE role_id=99001; INSERT IGNORE INTO sys_role_menu SELECT 99001,menu_id FROM sys_menu WHERE perms IN ('equipment:asset:query','equipment:asset:edit'); UPDATE ems_equipment_department SET dept_id=99001 WHERE equipment_id=99001;")
t=req('/login',body={'username':'race_reader','password':'admin123'})['token']
p='/equipment/assets/99001';b={'name':'scope-edit-A','status':'ACTIVE','location':'test-A'}
assert req(p,t,b,'PUT')['code']==200
assert req(p,t)['data']['name']=='scope-edit-A'
db('UPDATE ems_equipment_department SET dept_id=99002 WHERE equipment_id=99001')
b['name']='forbidden-edit'; assert req(p,t,b,'PUT')['code']!=200
db("UPDATE ems_equipment_department SET dept_id=99001 WHERE equipment_id=99001; DELETE rm FROM sys_role_menu rm JOIN sys_menu m ON m.menu_id=rm.menu_id WHERE rm.role_id=99001 AND m.perms='equipment:asset:edit'")
assert req(p,t,b,'PUT')['code']!=200
assert req(p,t)['data']['name']=='scope-edit-A'
print('asset edit same department, transferred device denial, revoked old token and unchanged name passed')
