#!/usr/bin/env python3
"""Experimental isolated HTTP test; uses existing scoped fixture accounts and records.
Requires EMS_ISOLATED_FIXTURE=YES, EMS_PHOTO_A_USER/PASSWORD, EMS_PHOTO_B_USER/PASSWORD,
EMS_PHOTO_A_DEVICE, EMS_PHOTO_B_DEVICE, EMS_PHOTO_A_INSPECTION, EMS_PHOTO_A_USER_ID.
Fixed development endpoint and container names. Leaves accepted synthetic photos in the isolated database.
"""
import base64, concurrent.futures, json, os, subprocess, urllib.error, urllib.request, uuid
if os.environ.get("EMS_ISOLATED_FIXTURE") != "YES": raise SystemExit("Refusing non-isolated execution")
BASE="http://127.0.0.1:18090/prod-api"
opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
def required(key):
 value=os.environ.get(key)
 if not value: raise SystemExit("Missing "+key)
 return value
def number(key):
 n=int(required(key))
 if n<=0: raise SystemExit("Invalid "+key)
 return n
def call(path,body=None,token=None,content_type="application/json",method=None):
 headers={"Content-Type":content_type}
 if token: headers["Authorization"]="Bearer "+token
 req=urllib.request.Request(BASE+path,body,headers,method=method or ("POST" if body is not None else "GET"))
 try:
  with opener.open(req,timeout=30) as r:return json.loads(r.read())
 except urllib.error.HTTPError as e:return {"code":e.code}
def login(prefix):
 r=call("/login",json.dumps({"username":required(prefix+"_USER"),"password":required(prefix+"_PASSWORD")}).encode())
 if "token" not in r: raise AssertionError("login failed")
 return r["token"]
def upload(path,token,equipment=None):
 boundary="fixture"+uuid.uuid4().hex
 data=b""
 if equipment is not None: data=("--"+boundary+"\r\nContent-Disposition: form-data; name=\"equipmentId\"\r\n\r\n"+str(equipment)+"\r\n").encode()
 data+=("--"+boundary+"\r\nContent-Disposition: form-data; name=\"file\"; filename=\"test.png\"\r\nContent-Type: image/png\r\n\r\n").encode()+PNG+("\r\n--"+boundary+"--\r\n").encode()
 return call(path,data,token,"multipart/form-data; boundary="+boundary)
def sql(query):
 p=subprocess.run(["docker","exec","-i","equipment-rebuild-mysql-1","sh","-c",'mysql -N -B -uroot -p"$MYSQL_ROOT_PASSWORD" equipment_dev 2>/dev/null'],input=query.encode(),capture_output=True,check=True)
 return p.stdout.decode().splitlines()
def check_file(name):
 assert name and "/" not in name and ".." not in name
 p=subprocess.run(["docker","exec","equipment-rebuild-backend-1","test","-f","/app/private-uploads/"+name])
 assert p.returncode==0, "database photo has no file"
PNG=base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/6x0AAAAASUVORK5CYII=')
a=login("EMS_PHOTO_A"); b=login("EMS_PHOTO_B")
da=number("EMS_PHOTO_A_DEVICE"); db=number("EMS_PHOTO_B_DEVICE"); ins=number("EMS_PHOTO_A_INSPECTION"); uid=number("EMS_PHOTO_A_USER_ID")
assert da!=db
assert sql(f"SELECT equipment_id FROM ems_inspection WHERE id={ins}")==[str(da)], "inspection fixture mismatch"
before=sql(f"SELECT (SELECT COUNT(*) FROM ems_inspection_photo_stage WHERE equipment_id={da}),(SELECT COUNT(*) FROM ems_inspection_photo WHERE inspection_id={ins})")
r1=upload("/equipment/inspections/staged-photos",b,da); r2=upload(f"/equipment/inspections/{ins}/photos",b)
assert r1.get("code") not in (200,503) and r2.get("code") not in (200,503),(r1,r2)
assert sql(f"SELECT (SELECT COUNT(*) FROM ems_inspection_photo_stage WHERE equipment_id={da}),(SELECT COUNT(*) FROM ems_inspection_photo WHERE inspection_id={ins})")==before
staged=upload("/equipment/inspections/staged-photos",a,da); assert staged.get("code")==200,staged
sid=int(staged["data"]["id"])
name=sql(f"SELECT stored_name FROM ems_inspection_photo_stage WHERE id={sid} AND equipment_id={da} AND uploaded_by={uid}")
assert len(name)==1; check_file(name[0])
removed=call(f"/equipment/inspections/staged-photos/{sid}",token=a,method="DELETE"); assert removed.get("code")==200,removed
assert not sql(f"SELECT id FROM ems_inspection_photo_stage WHERE id={sid}")
assert subprocess.run(["docker","exec","equipment-rebuild-backend-1","test","-f","/app/private-uploads/"+name[0]]).returncode != 0, "committed removal should clean unreferenced file"
# Two simultaneous requests: every accepted record must have its file; 503 is valid backpressure.
def send(_):return upload(f"/equipment/inspections/{ins}/photos",a)
with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool: results=list(pool.map(send,range(2)))
assert any(r.get("code")==200 for r in results),results
assert all(r.get("code") in (200,503) for r in results),results
for name in sql(f"SELECT stored_name FROM ems_inspection_photo WHERE inspection_id={ins} AND uploaded_by={uid}"):check_file(name)
photos=call(f"/equipment/inspections/{ins}/photos",token=a)
assert photos.get("code")==200 and photos.get("data"), "owner photo list missing"
photo_id=int(photos["data"][0]["id"])
foreign=call(f"/equipment/inspections/{ins}/photos",token=b)
assert foreign.get("code")!=200 or not foreign.get("data"), "cross-department photo list leaked"
def get_photo(token):
 req=urllib.request.Request(BASE+f"/equipment/inspections/photos/{photo_id}",headers={"Authorization":"Bearer "+token})
 try:
  with opener.open(req,timeout=30) as response:return response.status,response.read()
 except urllib.error.HTTPError as error:return error.code,b""
assert get_photo(a)[0]==200, "owner photo inaccessible"
assert get_photo(b)[0]!=200, "cross-department photo leaked"
print("isolated inspection photo scope, database/file consistency and concurrent upload passed")
