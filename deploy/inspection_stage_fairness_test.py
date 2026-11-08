import base64,json,subprocess,time,urllib.request,urllib.error,uuid
base='http://127.0.0.1:18090/prod-api'
def call(path,method='GET',data=None,token=None,content_type='application/json'):
 h={'Content-Type':content_type}
 if token:h['Authorization']='Bearer '+token
 if data is not None and not isinstance(data,bytes):data=json.dumps(data).encode()
 try:
  with urllib.request.urlopen(urllib.request.Request(base+path,data,h,method=method),timeout=30) as r:return json.load(r)
 except urllib.error.HTTPError as e:return {'code':e.code}
def sql(q):
 p=subprocess.run(['docker','exec','-i','equipment-rebuild-mysql-1','sh','-c','mysql -N -uroot -p"$MYSQL_ROOT_PASSWORD" equipment_dev 2>/dev/null'],input=q.encode(),capture_output=True);assert p.returncode==0,p.stderr;return p.stdout.decode().strip()
def login(n):return call('/login','POST',{'username':n,'password':'admin123'})['token']
a=login('admin');w=login('role_worker_test');tag=uuid.uuid4().hex;code='CLEAN-FAIR-'+tag[:8]
assert call('/equipment/assets','POST',{'code':code,'name':'cleanup fairness test'},a)['code']==200
eid=next(x['id'] for x in call('/equipment/assets?keyword='+code,token=a)['data'] if x['code']==code)
uid=int(sql("SELECT user_id FROM sys_user WHERE user_name='admin'"));prefix='fairness-'+tag+'-'
valid_id=None
try:
 values=','.join(f"({eid},{uid},'{prefix}{i}','image/png',1,DATE_SUB(NOW(),INTERVAL 4 HOUR))" for i in range(101))
 sql('INSERT INTO ems_inspection_photo_stage(equipment_id,uploaded_by,stored_name,media_type,file_size,expires_at) VALUES '+values)
 png=base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/6x0AAAAASUVORK5CYII=')
 b='---ems'+uuid.uuid4().hex
 payload=('--'+b+'\r\nContent-Disposition: form-data; name="equipmentId"\r\n\r\n'+str(eid)+'\r\n--'+b+'\r\nContent-Disposition: form-data; name="file"; filename="test.png"\r\nContent-Type: image/png\r\n\r\n').encode()+png+('\r\n--'+b+'--\r\n').encode()
 valid_id=call('/equipment/inspections/staged-photos','POST',payload,w,'multipart/form-data; boundary='+b)['data']['id']
 sql(f'UPDATE ems_inspection_photo_stage SET expires_at=DATE_SUB(NOW(),INTERVAL 2 HOUR) WHERE id={valid_id}')
 deadline=time.monotonic()+150
 while time.monotonic()<deadline:
  if sql(f'SELECT COUNT(*) FROM ems_inspection_photo_stage WHERE id={valid_id}')=='0':break
  time.sleep(4)
 else:raise AssertionError('invalid rows blocked cleanup of later valid photo')
 assert sql(f"SELECT COUNT(*) FROM ems_inspection_photo_stage WHERE equipment_id={eid} AND stored_name LIKE '{prefix}%'")=='101'
 print('invalid rows preserved; cleanup advanced to later valid photo')
finally:
 sql(f"DELETE FROM ems_inspection_photo_stage WHERE equipment_id={eid} AND stored_name LIKE '{prefix}%'")
 if valid_id:call('/equipment/inspections/staged-photos/'+str(valid_id),'DELETE',token=w)
