import json, os, subprocess, urllib.request
if os.environ.get("EMS_ISOLATED_FIXTURE")!="YES": raise SystemExit("isolated fixture required")
def db(sql): subprocess.run(["docker","exec","-i","inspection-scope-20261105-mysql-1","sh","-c",'mysql -uroot -p"$MYSQL_ROOT_PASSWORD" scope_test_race 2>/dev/null'],input=sql.encode(),check=True)
opener=urllib.request.build_opener(urllib.request.ProxyHandler({}));base="http://127.0.0.1:22091/prod-api"
def req(path,token=None,body=None):
 r=urllib.request.Request(base+path,None if body is None else json.dumps(body).encode(),{"Content-Type":"application/json",**({"Authorization":"Bearer "+token} if token else {})})
 with opener.open(r,timeout=15) as x:return json.load(x)
db("UPDATE sys_role SET status='0' WHERE role_id=99001; INSERT IGNORE INTO sys_role_menu SELECT 99001,menu_id FROM sys_menu WHERE perms IN ('equipment:inspection:list','equipment:order:report','equipment:order:list','equipment:order:accept'); UPDATE ems_equipment_department SET dept_id=99001 WHERE equipment_id=99001; INSERT INTO ems_inspection(id,equipment_id,inspector_id,inspected_at,result,remark) VALUES (99001,99001,1,NOW(),'ABNORMAL','scope-test') ON DUPLICATE KEY UPDATE result='ABNORMAL'; UPDATE ems_work_order SET inspection_id=NULL WHERE inspection_id=99001;")
db("INSERT IGNORE INTO ems_equipment(id,code,name) VALUES (99002,'INSP-B','Inspection B'); INSERT IGNORE INTO ems_equipment_department(equipment_id,dept_id) VALUES (99002,99002); INSERT IGNORE INTO ems_inspection(id,equipment_id,inspector_id,inspected_at,result,remark) VALUES (99002,99002,99001,NOW(),'ABNORMAL','own cross'),(99003,99002,1,NOW(),'ABNORMAL','foreign cross'); INSERT IGNORE INTO ems_work_order(id,equipment_id,inspection_id,reporter_id,description,status) VALUES (99002,99002,99002,1,'cross pending','REPORTED');")
db("UPDATE ems_inspection SET equipment_id=99002,inspector_id=99001,result='ABNORMAL' WHERE id=99002; UPDATE ems_inspection SET equipment_id=99002,inspector_id=1,result='ABNORMAL' WHERE id=99003; UPDATE ems_work_order SET equipment_id=99002,inspection_id=99002,reporter_id=1,technician_id=NULL,status='REPORTED' WHERE id=99002;")
t=req("/login",body={"username":"race_reader","password":"admin123"})["token"]
visible=req("/equipment/inspections/99002/work-orders",t); assert visible["code"]==200 and any(x["id"]==99002 for x in visible["data"]),"cross-department pending order hidden"
a=req("/equipment/inspections/99003/work-orders",t); b=req("/equipment/inspections/999999/work-orders",t); assert a["code"]==b["code"] and a["msg"]==b["msg"],"out-of-scope inspection disclosed"
def row():return next(x for x in req("/equipment/inspections",t)["data"] if x["id"]==99001)
assert row()["can_report"]==1,"scoped report entry hidden"
db("UPDATE ems_inspection SET inspector_id=99001 WHERE id=99001; UPDATE ems_equipment_department SET dept_id=99002 WHERE equipment_id=99001")
assert row()["can_report"]==0,"out-of-scope report offered"
assert req("/equipment/inspections/99001/work-order",t,{"description":"scope-test"})["code"]!=200
db("UPDATE ems_equipment_department SET dept_id=99001 WHERE equipment_id=99001")
assert req("/equipment/inspections/99001/work-order",t,{"description":"scope-test"})["code"]==200
assert row()["can_report"]==0,"duplicate report offered"
assert row()["order_id"] is not None,"associated order hidden"
r=req("/equipment/inspections/99001/work-orders",t); assert r["code"]==200 and len(r["data"])==1,"associated order query failed"
print("scoped inspection reporting entry, denial and duplicate guard passed")
