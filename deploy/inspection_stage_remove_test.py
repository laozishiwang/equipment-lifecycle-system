import base64, concurrent.futures, json, subprocess, urllib.request, urllib.error, uuid
base='http://127.0.0.1:18090/prod-api'
def call(path,method='GET',data=None,token=None,content_type='application/json'):
 h={'Content-Type':content_type}
 if token:h['Authorization']='Bearer '+token
 if data is not None and not isinstance(data,bytes):data=json.dumps(data).encode()
 try:
  with urllib.request.urlopen(urllib.request.Request(base+path,data,h,method=method),timeout=30) as r:return json.load(r)
 except urllib.error.HTTPError as e:return {'code':e.code}
def sql(q):
 p=subprocess.run(['docker','exec','-i','equipment-rebuild-mysql-1','sh','-c','mysql -N -uroot -p"$MYSQL_ROOT_PASSWORD" equipment_dev 2>/dev/null'],input=q.encode(),capture_output=True);assert p.returncode==0;return p.stdout.decode().strip()
def login(n):return call('/login','POST',{'username':n,'password':'admin123'})['token']
a=login('admin');w=login('role_worker_test');other=login('smoke_worker');code='STAGE-REMOVE-'+uuid.uuid4().hex[:8]
assert call('/equipment/assets','POST',{'code':code,'name':'stage remove test'},a)['code']==200
eid=next(x['id'] for x in call('/equipment/assets?keyword='+code,token=a)['data'] if x['code']==code)
png=base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/6x0AAAAASUVORK5CYII=')
def stage():
 b='---ems'+uuid.uuid4().hex
 payload=('--'+b+'\r\nContent-Disposition: form-data; name="equipmentId"\r\n\r\n'+str(eid)+'\r\n--'+b+'\r\nContent-Disposition: form-data; name="file"; filename="test.png"\r\nContent-Type: image/png\r\n\r\n').encode()+png+('\r\n--'+b+'--\r\n').encode()
 return call('/equipment/inspections/staged-photos','POST',payload,w,'multipart/form-data; boundary='+b)['data']['id']
def remove(id,token):return call('/equipment/inspections/staged-photos/'+str(id),'DELETE',token=token)
def submit(id):return call('/equipment/inspections','POST',{'equipmentId':eid,'result':'NORMAL','photoStageIds':[id]},w)
id=stage();name=sql(f'SELECT stored_name FROM ems_inspection_photo_stage WHERE id={id}')
remove(id,other)
assert sql(f'SELECT COUNT(*) FROM ems_inspection_photo_stage WHERE id={id}')=='1'
assert remove(id,w)['code']==200
assert sql(f'SELECT COUNT(*) FROM ems_inspection_photo_stage WHERE id={id}')=='0'
assert subprocess.run(['docker','exec','equipment-rebuild-backend-1','test','-e','/app/private-uploads/'+name]).returncode!=0
assert remove(id,w)['code']==200
bound=stage();r=submit(bound);assert r['code']==200;inspection=r['data']['inspectionId']
assert remove(bound,w)['code']!=200
photos=call(f'/equipment/inspections/{inspection}/photos',token=w)['data'];assert len(photos)==1
req=urllib.request.Request(base+'/equipment/inspections/photos/'+str(photos[0]['id']),headers={'Authorization':'Bearer '+w})
with urllib.request.urlopen(req,timeout=30) as response:assert response.read()==png
race=stage()
with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
 f1=pool.submit(remove,race,w);f2=pool.submit(submit,race);deleted=f1.result();submitted=f2.result()
assert (deleted['code']==200) != (submitted['code']==200),(deleted,submitted)
if submitted['code']==200:
 photos=call('/equipment/inspections/'+str(submitted['data']['inspectionId'])+'/photos',token=w)['data'];assert len(photos)==1
print('owner removal, idempotence, cross-user protection, bound preservation and submit race passed')
