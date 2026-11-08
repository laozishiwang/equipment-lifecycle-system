import concurrent.futures,datetime,json,threading,urllib.request,urllib.error,uuid
base='http://127.0.0.1:18090/prod-api'
def call(path,method='GET',data=None,token=None):
 h={'Content-Type':'application/json'}
 if token:h['Authorization']='Bearer '+token
 req=urllib.request.Request(base+path,None if data is None else json.dumps(data).encode(),h,method=method)
 try:
  with urllib.request.urlopen(req,timeout=20) as r:return json.load(r)
 except urllib.error.HTTPError as e:return {'code':e.code}
def login(name):return call('/login','POST',{'username':name,'password':'admin123'})['token']
a=login('admin');w=login('role_worker_test');t=login('role_tech_test');d=login('role_director_test')
for i in range(15):
 code='ASSIGN-RACE-'+uuid.uuid4().hex[:8];assert call('/equipment/assets','POST',{'code':code,'name':'race'},a)['code']==200
 eid=next(x['id'] for x in call('/equipment/assets?keyword='+code,token=a)['data'] if x['code']==code)
 assert call('/equipment/orders','POST',{'equipmentId':eid,'description':'race'},w)['code']==200
 oid=next(x['id'] for x in call('/equipment/orders',token=w)['data'] if x['equipment_id']==eid)
 assert call(f'/equipment/orders/{oid}/accept','POST',{},t)['code']==200
 assert call(f'/equipment/orders/{oid}/arrive','POST',{},t)['code']==200
 barrier=threading.Barrier(2)
 def assign():barrier.wait();return call(f'/equipment/orders/{oid}/assign','POST',{'technicianId':9003,'reason':'race'},d)['code']
 def complete():barrier.wait();return call(f'/equipment/orders/{oid}/complete','POST',{'repairDate':datetime.date.today().isoformat(),'description':'done','costs':[]},t)['code']
 with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
  x=pool.submit(assign);y=pool.submit(complete);codes=(x.result(),y.result())
 detail=call(f'/equipment/orders/{oid}',token=a)['data']
 assert codes[0]==200,repr(codes)
 if codes[1]==200:
  assert detail['status']=='TESTING' and detail['technician_id']==9003 and len(detail['assignments'])==1 and detail['repairs'][0]['technician_id']==9011
 else:
  assert detail['status']=='ARRIVED' and detail['technician_id']==9003 and len(detail['assignments'])==1 and len(detail['repairs'])==0
print('15 concurrent assignment and completion races passed')



