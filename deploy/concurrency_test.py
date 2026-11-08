import concurrent.futures, json, threading, urllib.request, uuid
base='http://127.0.0.1:18090/prod-api'
def call(path,method='GET',data=None,token=None):
 h={'Content-Type':'application/json'}
 if token:h['Authorization']='Bearer '+token
 with urllib.request.urlopen(urllib.request.Request(base+path,None if data is None else json.dumps(data).encode(),h,method=method),timeout=20) as r:return json.load(r)
t=call('/login','POST',{'username':'admin','password':'admin123'})['token']
for i in range(15):
 code='RACE-'+uuid.uuid4().hex[:10]
 assert call('/equipment/assets','POST',{'code':code,'name':'race test'},t)['code']==200
 eid=next(x['id'] for x in call('/equipment/assets',token=t)['data'] if x['code']==code)
 barrier=threading.Barrier(2)
 def report():
  barrier.wait();return call('/equipment/orders','POST',{'equipmentId':eid,'description':'race test'},t)['code']
 def retire():
  barrier.wait();return call(f'/equipment/assets/{eid}','PUT',{'name':'race test','status':'RETIRED'},t)['code']
 with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
  a=pool.submit(report);b=pool.submit(retire);codes=(a.result(),b.result())
 assert codes.count(200)==1, f'invalid results {codes}'
print('15 concurrent report/retire races preserved invariant')
