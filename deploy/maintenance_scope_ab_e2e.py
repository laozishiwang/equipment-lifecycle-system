import json,subprocess,urllib.request
base='http://127.0.0.1:22192/prod-api'
def db(s): subprocess.run(['docker','exec','-i','maint-scope-20261106-mysql-1','sh','-c','mysql -uroot -p"$MYSQL_ROOT_PASSWORD" scope_test_race 2>/dev/null'],input=s.encode(),check=True)
def req(path,method='GET',data=None,token=None):
 r=urllib.request.Request(base+path,None if data is None else json.dumps(data).encode(),{'Content-Type':'application/json',**({'Authorization':'Bearer '+token} if token else {})},method=method)
 with urllib.request.urlopen(r,timeout=20) as x:return json.load(x)
db("INSERT IGNORE INTO sys_role_menu SELECT 99001,menu_id FROM sys_menu WHERE perms IN ('equipment:maintenance:list','equipment:maintenance:add','equipment:maintenance:edit','equipment:maintenance:complete'); INSERT INTO ems_equipment(id,code,name) VALUES(99002,'MAINT-B','Maint B'); INSERT INTO ems_equipment_department(equipment_id,dept_id) VALUES(99002,99002); INSERT INTO ems_maintenance_plan(id,equipment_id,title,interval_days,next_due,created_by) VALUES(99001,99001,'Maint A',30,'2020-01-01',1),(99002,99002,'Maint B',30,'2020-01-01',1);")
t=req('/login','POST',{'username':'race_reader','password':'admin123'})['token']
r=req('/equipment/maintenance',token=t); assert r['code']==200 and any(x['id']==99001 for x in r['data']) and not any(x['id']==99002 for x in r['data']),r
r=req('/equipment/maintenance/99002/deactivate','POST',{},t); assert r['code']!=200,r
r=req('/equipment/maintenance','POST',{'equipmentId':99002,'title':'forbidden','intervalDays':30,'nextDue':'2026-11-06'},t); assert r['code']!=200,r
r=req('/equipment/maintenance/99001','PUT',{'title':'Maint A edited','intervalDays':30,'nextDue':'2020-01-01'},t); assert r['code']==200,r
summary=req('/equipment/maintenance/due-summary',token=t); assert summary['code']==200 and int(summary['data']['overdue'])==1,summary
r=req('/equipment/maintenance/99002/complete','POST',{'completedDate':'2026-11-01','notes':'forbidden'},t); assert r['code']!=200,r
r=req('/equipment/maintenance/99001/complete','POST',{'completedDate':'2026-11-01','notes':'done'},t); assert r['code']==200,r
db("UPDATE ems_equipment_department SET dept_id=99002 WHERE equipment_id=99001")
r=req('/equipment/maintenance',token=t); assert not any(x['id']==99001 for x in r['data']),r
r=req('/equipment/maintenance/99001/complete','POST',{'completedDate':'2026-11-05','notes':'transferred'},t); assert r['code']!=200,r
db("UPDATE ems_equipment_department SET dept_id=99001 WHERE equipment_id=99001; DELETE rm FROM sys_role_menu rm JOIN sys_menu m ON m.menu_id=rm.menu_id WHERE rm.role_id=99001 AND m.perms='equipment:maintenance:complete'")
r=req('/equipment/maintenance/99001/complete','POST',{'completedDate':'2026-11-05','notes':'revoked'},t); assert r['code']!=200,r
db("DELETE rm FROM sys_role_menu rm JOIN sys_menu m ON m.menu_id=rm.menu_id WHERE rm.role_id=99001 AND m.perms='equipment:maintenance:edit'")
r=req('/equipment/maintenance/99001/deactivate','POST',{},t); assert r['code']!=200,r
print('maintenance A/B list, create, direct-ID edit/deactivate and old-token revocation passed')
