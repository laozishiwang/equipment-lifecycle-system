import base64,json,subprocess,urllib.request,urllib.error,uuid
base="http://127.0.0.1:22207/prod-api/public/field/99001"
def db(s):
 return subprocess.check_output(["docker","exec","-i","public-field-test-20261107-mysql-1","sh","-c",'mysql -N -B -uroot -p"$MYSQL_ROOT_PASSWORD" scope_test_race 2>/dev/null'],input=s.encode()).decode()
def req(path="",data=None):
 r=urllib.request.Request(base+path,None if data is None else json.dumps(data).encode(),{"Content-Type":"application/json"})
 with urllib.request.urlopen(r,timeout=20) as x:return json.load(x)
def upload():
 b="--x"+uuid.uuid4().hex; png=base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/6x0AAAAASUVORK5CYII=")
 body=("--"+b+"\r\nContent-Disposition: form-data; name=\"file\"; filename=\"x.png\"\r\nContent-Type: image/png\r\n\r\n").encode()+png+("\r\n--"+b+"--\r\n").encode()
 r=urllib.request.Request(base+"/photos",body,{"Content-Type":"multipart/form-data; boundary="+b})
 with urllib.request.urlopen(r,timeout=20) as x:return json.load(x)["data"]["token"]
db("INSERT INTO ems_inspection_template(id,name,created_by) VALUES(99001,'Test',1); INSERT INTO ems_inspection_template_item(id,template_id,item_name,sort_order) VALUES(99001,99001,'Temperature',0); INSERT INTO ems_equipment_inspection_template(equipment_id,template_id) VALUES(99001,99001); INSERT INTO ems_inspection_numeric_rule(template_item_id,lower_bound,upper_bound) VALUES(99001,1,10); INSERT INTO ems_inspection_photo_rule(template_id,require_abnormal_photo) VALUES(99001,1);")
a=req();assert a["code"]==200 and a["data"]["templates"][0]["id"]==99001,a
assert req("/reports",{"name":"","description":"broken"})["code"]!=200
db("INSERT INTO ems_inspection_photo_stage(equipment_id,uploaded_by,stored_name,media_type,file_size,expires_at) SELECT 99001,u.user_id,CONCAT('quota-test-',n.i,'.png'),'image/png',1,DATE_ADD(NOW(),INTERVAL 1 HOUR) FROM sys_user u JOIN (SELECT 1 i UNION SELECT 2 UNION SELECT 3 UNION SELECT 4 UNION SELECT 5 UNION SELECT 6 UNION SELECT 7 UNION SELECT 8 UNION SELECT 9 UNION SELECT 10 UNION SELECT 11 UNION SELECT 12 UNION SELECT 13 UNION SELECT 14 UNION SELECT 15 UNION SELECT 16 UNION SELECT 17 UNION SELECT 18 UNION SELECT 19 UNION SELECT 20 UNION SELECT 21 UNION SELECT 22 UNION SELECT 23 UNION SELECT 24) n WHERE u.user_name='ems_field_guest'")
photo=upload();db("DELETE FROM ems_inspection_photo_stage WHERE stored_name LIKE 'quota-test-%'"); report=req("/reports",{"name":"WorkerA","description":"broken","photoTokens":[photo]});assert report["code"]==200,report
order=report["data"]["orderId"];assert db(f"SELECT reporter_name FROM ems_work_order WHERE id={order}").strip()=="WorkerA";assert db(f"SELECT COUNT(*) FROM ems_work_order_photo WHERE work_order_id={order}").strip()=="1"
photo=upload(); inspect=req("/inspections",{"name":"WorkerB","result":"ABNORMAL","remark":"broken","createOrder":True,"templateId":99001,"items":[{"name":"Temperature","result":"ABNORMAL","measuredValue":11}],"photoTokens":[photo]});assert inspect["code"]==200,inspect
id=inspect["data"]["inspectionId"];assert db(f"SELECT inspector_name FROM ems_inspection WHERE id={id}").strip()=="WorkerB";assert db(f"SELECT COUNT(*) FROM ems_inspection_template_snapshot WHERE inspection_id={id}").strip()=="1";assert db(f"SELECT COUNT(*) FROM ems_inspection_photo WHERE inspection_id={id}").strip()=="1"
assert req("/inspections",{"name":"WorkerB","result":"NORMAL","templateId":99001,"items":[{"name":"Temperature","result":"NORMAL","measuredValue":11}]})["code"]!=200
print("public field report, inspection, numeric rule, snapshot, actor names and photos passed")

def api(path,token=None,data=None):
 r=urllib.request.Request("http://127.0.0.1:22207/prod-api"+path,None if data is None else json.dumps(data).encode(),{"Content-Type":"application/json",**({"Authorization":"Bearer "+token} if token else {})})
 with urllib.request.urlopen(r,timeout=20) as x:return json.load(x)
token=api("/login",data={"username":"admin","password":"admin123"})["token"]
detail=api(f"/equipment/orders/{order}",token);assert detail["code"]==200 and detail["data"]["reporter_name"]=="WorkerA",detail
photos=api(f"/equipment/orders/{order}/photos",token);assert photos["code"]==200 and len(photos["data"])==1,photos
r=urllib.request.Request("http://127.0.0.1:22207/prod-api/equipment/orders/photos/"+str(photos["data"][0]["id"]),headers={"Authorization":"Bearer "+token})
with urllib.request.urlopen(r,timeout=20) as x: assert x.read()==base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/6x0AAAAASUVORK5CYII=")
for path,payload in [("accept",{}),("arrive",{}),("complete",{"repairDate":"2026-11-07","description":"fixed","costs":[{"category":"LABOR","description":"labour","amount":20},{"category":"PARTS","description":"parts","amount":30}]}),("trial",{"result":"PASS","notes":"ok"}),("close",{})]:
 r=api(f"/equipment/orders/{order}/{path}",token,payload);assert r["code"]==200,(path,r)
detail=api(f"/equipment/orders/{order}",token)["data"];assert detail["status"]=="CLOSED" and detail["reporter_name"]=="WorkerA",detail
assert [(x["from_status"],x["to_status"]) for x in detail["transitions"]]==[("NEW","REPORTED"),("REPORTED","ACCEPTED"),("ACCEPTED","ARRIVED"),("ARRIVED","TESTING"),("TESTING","COMPLETED"),("COMPLETED","CLOSED")]
print("anonymous report photo downloaded by director, repair costs and closure audit passed")
