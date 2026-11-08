import datetime,json,urllib.request,urllib.error,uuid
base='http://127.0.0.1:18090/prod-api'
def call(path,method='GET',data=None,token=None):
 h={'Content-Type':'application/json'}
 if token:h['Authorization']='Bearer '+token
 req=urllib.request.Request(base+path,None if data is None else json.dumps(data).encode(),h,method=method)
 try:
  with urllib.request.urlopen(req,timeout=30) as r:return json.load(r)
 except urllib.error.HTTPError as e:return {'code':e.code}
def login(name):return call('/login','POST',{'username':name,'password':'admin123'})['token']
a=login('admin');w=login('role_worker_test');t=login('role_tech_test');other=login('smoke_tech_b');director=login('role_director_test');code='ASSIGN-'+uuid.uuid4().hex[:10]
assert call('/equipment/assets','POST',{'code':code,'name':'assignment test'},a)['code']==200
eid=next(x['id'] for x in call('/equipment/assets?keyword='+code,token=a)['data'] if x['code']==code)
assert call('/equipment/orders','POST',{'equipmentId':eid,'description':'assignment test'},w)['code']==200
oid=next(x['id'] for x in call('/equipment/orders',token=w)['data'] if x['equipment_id']==eid)
assert call(f'/equipment/orders/{oid}/assign','POST',{'technicianId':9003,'reason':'test'},director)['code']!=200
assert call(f'/equipment/orders/{oid}/accept','POST',{},t)['code']==200
assert call(f'/equipment/orders/{oid}/arrive','POST',{},t)['code']==200
people=call('/equipment/orders/technicians',token=director)['data'];assert any(x['user_id']==9003 for x in people) and not any(x['user_id']==9010 for x in people)
assert call(f'/equipment/orders/{oid}/assign','POST',{'technicianId':9010,'reason':'invalid'},director)['code']!=200
assert call(f'/equipment/orders/{oid}/assign','POST',{'technicianId':9003,'reason':'unauthorized'},t)['code'] in (401,403)
assert call(f'/equipment/orders/{oid}/assign','POST',{'technicianId':9003,'reason':'shift handover'},director)['code']==200
detail=call(f'/equipment/orders/{oid}',token=director)['data'];assert detail['status']=='ARRIVED' and detail['technician_id']==9003 and detail['assignments'][0]['reason']=='shift handover'
payload={'repairDate':datetime.date.today().isoformat(),'description':'fixed','costs':[]}
assert call(f'/equipment/orders/{oid}/complete','POST',payload,t)['code']!=200
assert call(f'/equipment/orders/{oid}/complete','POST',payload,other)['code']==200
assert call(f'/equipment/orders/{oid}/trial','POST',{'result':'PASS','notes':'ok'},other)['code']==200
assert call(f'/equipment/orders/{oid}/assign','POST',{'technicianId':9011,'reason':'late'},director)['code']!=200
print('assignment permission, eligibility, history and technician ownership passed')


