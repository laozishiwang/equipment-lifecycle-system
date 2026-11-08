import json,os,subprocess,urllib.request,urllib.error
if os.environ.get('EMS_ISOLATED_FIXTURE')!='YES': raise SystemExit('isolated fixture required')
def db(s): subprocess.run(['docker','exec','-i','scope-inspect-create-20261106-mysql-1','sh','-c','mysql -uroot -p"$MYSQL_ROOT_PASSWORD" scope_test_race 2>/dev/null'],input=s.encode(),check=True)
def req(path,token=None,body=None,method=None):
 r=urllib.request.Request('http://127.0.0.1:22195/prod-api'+path,None if body is None else json.dumps(body).encode(),{'Content-Type':'application/json',**({'Authorization':'Bearer '+token} if token else {})},method=method)
 try:
  with urllib.request.urlopen(r,timeout=15) as x:return json.load(x)
 except urllib.error.HTTPError as e:return {'code':e.code}
db("UPDATE sys_role SET status='0',data_scope='3' WHERE role_id=99001; INSERT IGNORE INTO sys_role_menu SELECT 99001,menu_id FROM sys_menu WHERE perms IN ('equipment:inspection:add','equipment:inspection:list'); UPDATE ems_equipment_department SET dept_id=99001 WHERE equipment_id=99001;")
t=req('/login',body={'username':'race_reader','password':'admin123'})['token']
b={'equipmentId':99001,'result':'NORMAL','remark':'scope test'}
r=req('/equipment/inspections',t,b,'POST'); assert r['code']==200
inspection_id=r['data']['inspectionId']
db(f'UPDATE ems_inspection SET inspector_id=1 WHERE id={inspection_id}')
for suffix in ('items','template-snapshot'):
 result=req(f'/equipment/inspections/{inspection_id}/{suffix}',t); assert result['code']==200, result
db('UPDATE ems_equipment_department SET dept_id=99002 WHERE equipment_id=99001')
for suffix in ('items','template-snapshot'):
 assert req(f'/equipment/inspections/{inspection_id}/{suffix}',t)['code']!=200
assert req('/equipment/inspections',t,b,'POST')['code']!=200
db("UPDATE ems_equipment_department SET dept_id=99001 WHERE equipment_id=99001; DELETE rm FROM sys_role_menu rm JOIN sys_menu m ON m.menu_id=rm.menu_id WHERE rm.role_id=99001 AND m.perms='equipment:inspection:add'")
assert req('/equipment/inspections',t,b,'POST')['code']!=200
db("DELETE rm FROM sys_role_menu rm JOIN sys_menu m ON m.menu_id=rm.menu_id WHERE rm.role_id=99001 AND m.perms='equipment:inspection:list'")
for suffix in ('items','template-snapshot'):
 assert req(f'/equipment/inspections/{inspection_id}/{suffix}',t)['code']!=200
print('inspection creation same department, transfer denial, old token revocation passed')
