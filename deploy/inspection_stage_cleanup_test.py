import base64, concurrent.futures, json, subprocess, time, urllib.request, urllib.error, uuid
base='http://127.0.0.1:18090/prod-api'
def call(path,method='GET',data=None,token=None,content_type='application/json'):
 h={'Content-Type':content_type}
 if token:h['Authorization']='Bearer '+token
 if data is not None and not isinstance(data,bytes):data=json.dumps(data).encode()
 try:
  with urllib.request.urlopen(urllib.request.Request(base+path,data,h,method=method),timeout=30) as r:return json.load(r)
 except urllib.error.HTTPError as e:return {'code':e.code}
def sql(s):
 p=subprocess.run(['docker','exec','-i','equipment-rebuild-mysql-1','sh','-c','mysql -N -uroot -p"$MYSQL_ROOT_PASSWORD" equipment_dev 2>/dev/null'],input=s.encode(),capture_output=True);assert p.returncode==0,p.stderr;return p.stdout.decode().strip()
a=call('/login','POST',{'username':'admin','password':'admin123'})['token'];w=call('/login','POST',{'username':'role_worker_test','password':'admin123'})['token']
code='STAGE-CLEAN-'+uuid.uuid4().hex[:8]
assert call('/equipment/assets','POST',{'code':code,'name':'stage cleanup test'},a)['code']==200
eid=next(x['id'] for x in call('/equipment/assets?keyword='+code,token=a)['data'] if x['code']==code)
png=base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/6x0AAAAASUVORK5CYII=')
def stage():
 b='---ems'+uuid.uuid4().hex
 data=('--'+b+'\r\nContent-Disposition: form-data; name="equipmentId"\r\n\r\n'+str(eid)+'\r\n--'+b+'\r\nContent-Disposition: form-data; name="file"; filename="test.png"\r\nContent-Type: image/png\r\n\r\n').encode()+png+('\r\n--'+b+'--\r\n').encode()
 return call('/equipment/inspections/staged-photos','POST',data,w,'multipart/form-data; boundary='+b)
bound=stage()['data']['id']
r=call('/equipment/inspections','POST',{'equipmentId':eid,'result':'NORMAL','photoStageIds':[bound]},w);assert r['code']==200,r
inspection=r['data']['inspectionId'];photos=call(f'/equipment/inspections/{inspection}/photos',token=w)['data'];assert len(photos)==1
expired=stage()['data']['id'];fresh=stage()['data']['id']
expired_name=sql(f'SELECT stored_name FROM ems_inspection_photo_stage WHERE id={expired}')
sql(f"UPDATE ems_inspection_photo_stage SET expires_at=DATE_SUB(NOW(),INTERVAL 2 HOUR) WHERE id IN ({expired},{bound})")
# Concurrent uploads must never exceed the per-user cap. Retry 503 image decoder overloads.
def attempt(_):
 for n in range(20):
  x=stage()
  if x.get('code')!=503:return x
  time.sleep(.15)
 return x
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:results=list(pool.map(attempt,range(28)))
assert all(x['code']==200 or x.get('code')==500 for x in results),results
uid=sql("SELECT user_id FROM sys_user WHERE user_name='role_worker_test'")
assert int(sql(f'SELECT COUNT(*) FROM ems_inspection_photo_stage WHERE uploaded_by={uid} AND inspection_id IS NULL'))<=24
assert any(x['code']!=200 for x in results)
# Only expire test-owned rows. Leave any other user's data untouched.
ids=[fresh]+[x['data']['id'] for x in results if x['code']==200]
sql('UPDATE ems_inspection_photo_stage SET expires_at=DATE_SUB(NOW(),INTERVAL 2 HOUR) WHERE id IN ('+','.join(map(str,ids))+')')
deadline=time.monotonic()+150
while time.monotonic()<deadline:
 if sql(f'SELECT COUNT(*) FROM ems_inspection_photo_stage WHERE id={expired}')=='0':break
 time.sleep(3)
else:raise AssertionError('expired stage not cleaned')
assert subprocess.run(['docker','exec','equipment-rebuild-backend-1','test','-e','/app/private-uploads/'+expired_name]).returncode!=0
assert sql(f'SELECT COUNT(*) FROM ems_inspection_photo_stage WHERE id={bound}')=='1'
assert call(f'/equipment/inspections/{inspection}/photos',token=w)['data'][0]['id']==photos[0]['id']
request=urllib.request.Request(base+'/equipment/inspections/photos/'+str(photos[0]['id']),headers={'Authorization':'Bearer '+w})
with urllib.request.urlopen(request,timeout=30) as response:assert response.read()==png
print('expired cleanup, bound photo preservation, concurrent per-user quota passed')
