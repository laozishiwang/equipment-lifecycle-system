import json,urllib.request,urllib.error,uuid
base='http://127.0.0.1:18090/prod-api'
def call(path,method='GET',data=None,token=None):
 h={'Content-Type':'application/json'}
 if token:h['Authorization']='Bearer '+token
 req=urllib.request.Request(base+path,None if data is None else json.dumps(data).encode(),h,method=method)
 try:
  with urllib.request.urlopen(req,timeout=15) as r:return json.load(r)
 except urllib.error.HTTPError as e:return {'code':e.code}
def login(name):return call('/login','POST',{'username':name,'password':'admin123'})['token']
a=login('admin');w=login('role_worker_test');other=login('smoke_worker');tech=login('role_tech_test');director=login('role_director_test');code='CANCEL-'+uuid.uuid4().hex[:10]
assert call('/equipment/assets','POST',{'code':code,'name':'cancel test'},a)['code']==200
eid=next(x['id'] for x in call('/equipment/assets?keyword='+code,token=a)['data'] if x['code']==code)
assert call('/equipment/orders','POST',{'equipmentId':eid,'description':'withdraw test'},w)['code']==200
oid=next(x['id'] for x in call('/equipment/orders',token=w)['data'] if x['equipment_id']==eid)
assert call(f'/equipment/orders/{oid}/withdraw','POST',{'reason':'other'},other)['code']!=200
assert call(f'/equipment/orders/{oid}/withdraw','POST',{'reason':' '},w)['code']!=200
assert call(f'/equipment/orders/{oid}/withdraw','POST',{'reason':'mistake'},w)['code']==200
detail=call(f'/equipment/orders/{oid}',token=w)['data'];assert detail['status']=='CANCELLED' and detail['cancellation']['reason']=='mistake'
assert [(x['from_status'],x['to_status']) for x in detail['transitions']]==[('NEW','REPORTED'),('REPORTED','CANCELLED')]
assert call('/equipment/orders','POST',{'equipmentId':eid,'description':'cancel test'},w)['code']==200
oid2=next(x['id'] for x in call('/equipment/orders',token=w)['data'] if x['equipment_id']==eid and x['id']!=oid)
assert call(f'/equipment/orders/{oid2}/accept','POST',{},tech)['code']==200
assert call(f'/equipment/orders/{oid2}/withdraw','POST',{'reason':'late'},w)['code']!=200
assert call(f'/equipment/orders/{oid2}/cancel','POST',{'reason':'no'},tech)['code'] in (401,403)
assert call(f'/equipment/orders/{oid2}/cancel','POST',{'reason':'director cancel'},director)['code']==200
assert call(f'/equipment/orders/{oid2}/cancel','POST',{'reason':'again'},director)['code']!=200
assert call(f'/equipment/assets/{eid}','PUT',{'name':'cancel test','status':'RETIRED'},a)['code']==200
print('withdrawal, cancellation, permissions, audit and retirement passed')
