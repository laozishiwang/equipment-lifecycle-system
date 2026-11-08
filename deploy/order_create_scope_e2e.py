import json,os,subprocess,urllib.request,urllib.error
if os.environ.get('EMS_ISOLATED_FIXTURE')!='YES': raise SystemExit('isolated fixture required')
def db(s): subprocess.run(['docker','exec','-i','scope-order-create-20261106-mysql-1','sh','-c','mysql -uroot -p"$MYSQL_ROOT_PASSWORD" scope_test_race 2>/dev/null'],input=s.encode(),check=True)
def req(path,token=None,body=None,method=None):
 r=urllib.request.Request('http://127.0.0.1:22194/prod-api'+path,None if body is None else json.dumps(body).encode(),{'Content-Type':'application/json',**({'Authorization':'Bearer '+token} if token else {})},method=method)
 try:
  with urllib.request.urlopen(r,timeout=15) as x:return json.load(x)
 except urllib.error.HTTPError as e:return {'code':e.code}
db("UPDATE sys_role SET status='0',data_scope='3' WHERE role_id=99001; INSERT IGNORE INTO sys_role_menu SELECT 99001,menu_id FROM sys_menu WHERE perms IN ('equipment:order:report','equipment:order:list','equipment:order:cancel'); UPDATE ems_equipment_department SET dept_id=99001 WHERE equipment_id=99001;")
t=req('/login',body={'username':'race_reader','password':'admin123'})['token']
b={'equipmentId':99001,'description':'scope order allowed'}
created=req('/equipment/orders',t,b,'POST'); assert created['code']==200; oid=created['data']['id']
db('UPDATE ems_equipment_department SET dept_id=99002 WHERE equipment_id=99001')
b['description']='scope order denied'; assert req('/equipment/orders',t,b,'POST')['code']!=200
assert req(f'/equipment/orders/{oid}/cancel',t,{'reason':'outside department'},'POST')['code']!=200
assert req(f'/equipment/orders/{oid}/withdraw',t,{'reason':'reporter after transfer'},'POST')['code']==200
assert req(f'/equipment/orders/{oid}/withdraw',t,{'reason':'duplicate'},'POST')['code']!=200
db('UPDATE ems_equipment_department SET dept_id=99001 WHERE equipment_id=99001')
cancel_order=req('/equipment/orders',t,{'equipmentId':99001,'description':'same department cancellation'},'POST')
assert cancel_order['code']==200, cancel_order
cancel_id=cancel_order['data']['id']
cancelled=req(f'/equipment/orders/{cancel_id}/cancel',t,{'reason':'same department cancellation'},'POST')
assert cancelled['code']==200, cancelled
assert req(f'/equipment/orders/{cancel_id}/cancel',t,{'reason':'duplicate'},'POST')['code']!=200
revoked_order=req('/equipment/orders',t,{'equipmentId':99001,'description':'cancel revocation'},'POST')
assert revoked_order['code']==200, revoked_order
revoked_id=revoked_order['data']['id']
db("DELETE rm FROM sys_role_menu rm JOIN sys_menu m ON m.menu_id=rm.menu_id WHERE rm.role_id=99001 AND m.perms='equipment:order:cancel'")
assert req(f'/equipment/orders/{revoked_id}/cancel',t,{'reason':'revoked'},'POST')['code']!=200
assert req(f'/equipment/orders/{revoked_id}/withdraw',t,{'reason':'still reporter'},'POST')['code']==200
db("UPDATE ems_equipment_department SET dept_id=99001 WHERE equipment_id=99001; DELETE rm FROM sys_role_menu rm JOIN sys_menu m ON m.menu_id=rm.menu_id WHERE rm.role_id=99001 AND m.perms='equipment:order:report'")
assert req('/equipment/orders',t,b,'POST')['code']!=200
print('order creation same department, transfer denial, old token revocation, reporter withdrawal after transfer and duplicate withdrawal passed')
