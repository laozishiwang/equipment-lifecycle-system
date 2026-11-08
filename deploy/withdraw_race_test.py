import concurrent.futures,json,threading,urllib.request,urllib.error,uuid
base='http://127.0.0.1:18090/prod-api'
def call(path,method='GET',data=None,token=None):
 h={'Content-Type':'application/json'}
 if token:h['Authorization']='Bearer '+token
 req=urllib.request.Request(base+path,None if data is None else json.dumps(data).encode(),h,method=method)
 try:
  with urllib.request.urlopen(req,timeout=20) as r:return json.load(r)
 except urllib.error.HTTPError as e:return {'code':e.code}
def login(user):return call('/login','POST',{'username':user,'password':'admin123'})['token']
a=login('admin');w=login('role_worker_test');t=login('role_tech_test')
for i in range(15):
 code='WITHDRAW-RACE-'+uuid.uuid4().hex[:8]
 assert call('/equipment/assets','POST',{'code':code,'name':'race'},a)['code']==200
 eid=next(x['id'] for x in call('/equipment/assets?keyword='+code,token=a)['data'] if x['code']==code)
 assert call('/equipment/orders','POST',{'equipmentId':eid,'description':'race'},w)['code']==200
 oid=next(x['id'] for x in call('/equipment/orders',token=w)['data'] if x['equipment_id']==eid)
 barrier=threading.Barrier(2)
 def accept():barrier.wait();return call(f'/equipment/orders/{oid}/accept','POST',{},t)['code']
 def withdraw():barrier.wait();return call(f'/equipment/orders/{oid}/withdraw','POST',{'reason':'race'},w)['code']
 with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
  x=pool.submit(accept);y=pool.submit(withdraw);codes=(x.result(),y.result())
 assert codes.count(200)==1,repr(codes)
 detail=call(f'/equipment/orders/{oid}',token=a)['data'];assert detail['status'] in ('ACCEPTED','CANCELLED') and len(detail['transitions'])==2
print('15 concurrent acceptance and withdrawal races passed')
