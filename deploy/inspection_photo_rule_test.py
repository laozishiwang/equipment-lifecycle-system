import base64,concurrent.futures,json,subprocess,urllib.request,urllib.error,uuid
base='http://127.0.0.1:18090/prod-api'
def call(path,method='GET',data=None,token=None,raw=False,content_type='application/json'):
 h={'Content-Type':content_type}
 if token:h['Authorization']='Bearer '+token
 req=urllib.request.Request(base+path,data if raw else (None if data is None else json.dumps(data).encode()),h,method=method)
 try:
  with urllib.request.urlopen(req,timeout=30) as r:
   payload=r.read();return (r.status,r.headers,payload) if raw and method=='GET' else json.loads(payload)
 except urllib.error.HTTPError as e:return {'code':e.code}
def login(name):return call('/login','POST',{'username':name,'password':'admin123'})['token']
def stage(equipment,token,body):
 boundary='---ems'+uuid.uuid4().hex
 payload=('--'+boundary+'\r\nContent-Disposition: form-data; name="equipmentId"\r\n\r\n'+str(equipment)+'\r\n--'+boundary+'\r\nContent-Disposition: form-data; name="file"; filename="test.png"\r\nContent-Type: image/png\r\n\r\n').encode()+body+('\r\n--'+boundary+'--\r\n').encode()
 return call('/equipment/inspections/staged-photos','POST',payload,token,True,'multipart/form-data; boundary='+boundary)
a=login('admin');w=login('role_worker_test');other=login('smoke_worker');code='PHOTO-RULE-'+uuid.uuid4().hex[:8]
assert call('/equipment/assets','POST',{'code':code,'name':'photo rule test'},a)['code']==200
eid=next(x['id'] for x in call('/equipment/assets?keyword='+code,token=a)['data'] if x['code']==code)
path=f'/equipment/assets/{eid}/inspection-template'
payload={'name':'photo rule test','requireAbnormalPhoto':True,'items':[{'name':'check'}]}
t=call(path,'PUT',payload,a)['data']['id'];assert call(path,token=w)['data']['requireAbnormalPhoto'] is True
# An older editor that omits the option must not silently disable a required rule.
t=call(path,'PUT',{'name':'legacy editor','items':[{'name':'check'}]},a)['data']['id'];assert call(path,token=w)['data']['requireAbnormalPhoto'] is True
png=base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/6x0AAAAASUVORK5CYII=')
assert stage(eid,w,png[:33])['code']!=200
s=stage(eid,w,png);assert s['code']==200;sid=s['data']['id']
def submit(token,photos,result='ABNORMAL'):
 return call('/equipment/inspections','POST',{'equipmentId':eid,'result':result,'remark':'test','templateId':t,'items':[{'name':'check','result':result}],'photoStageIds':photos},token)
assert submit(w,[])['code']!=200
assert submit(other,[sid])['code']!=200
r=submit(w,[sid]);assert r['code']==200;inspection=r['data']['inspectionId']
photos=call(f'/equipment/inspections/{inspection}/photos',token=w)['data'];assert len(photos)==1
status,headers,body=call('/equipment/inspections/photos/'+str(photos[0]['id']),token=w,raw=True);assert status==200 and body==png
assert submit(w,[sid])['code']!=200
assert submit(w,[],'NORMAL')['code']==200
pending=stage(eid,w,png)['data']['id']
assert submit(w,[pending,pending])['code']!=200
assert call('/equipment/inspections','POST',{'equipmentId':1,'result':'NORMAL','photoStageIds':[pending]},w)['code']!=200
with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool: race=list(pool.map(lambda _:submit(w,[pending]),range(2)))
assert sum(x['code']==200 for x in race)==1,race
expired=stage(eid,w,png)['data']['id']
sql='UPDATE ems_inspection_photo_stage SET expires_at=DATE_SUB(NOW(),INTERVAL 1 SECOND) WHERE id='+str(int(expired))
p=subprocess.run(['docker','exec','-i','equipment-rebuild-mysql-1','sh','-c','mysql -uroot -p"$MYSQL_ROOT_PASSWORD" equipment_dev 2>/dev/null'],input=sql.encode(),capture_output=True);assert p.returncode==0
assert submit(w,[expired])['code']!=200
print('required anomaly photo, ownership, binding, replay and normal compatibility passed')
