import json,urllib.request,uuid
base='http://127.0.0.1:18090/prod-api'
def call(path,method='GET',data=None,token=None):
 h={'Content-Type':'application/json'}
 if token:h['Authorization']='Bearer '+token
 with urllib.request.urlopen(urllib.request.Request(base+path,None if data is None else json.dumps(data).encode(),h,method=method),timeout=15) as r:return json.load(r)
def login(user):return call('/login','POST',{'username':user,'password':'admin123'})['token']
a=login('admin');w=login('smoke_worker');tech=login('smoke_tech_a');code='SCOPE-'+uuid.uuid4().hex[:10]
assert call('/equipment/assets','POST',{'code':code,'name':'scope test'},a)['code']==200
eid=next(x['id'] for x in call('/equipment/assets',token=a)['data'] if x['code']==code)
assert call('/equipment/orders','POST',{'equipmentId':eid,'description':'admin order'},a)['code']==200
assert call('/equipment/orders','POST',{'equipmentId':eid,'description':'worker order'},w)['code']==200
adminorders=call('/equipment/orders',token=a)['data'];mine=call('/equipment/orders',token=w)['data'];pending=call('/equipment/orders',token=tech)['data']
assert any(x['equipment_id']==eid and x['description']=='admin order' for x in adminorders)
assert not any(x['equipment_id']==eid and x['description']=='admin order' for x in mine)
assert any(x['equipment_id']==eid and x['description']=='worker order' for x in mine)
assert any(x['equipment_id']==eid and x['description']=='admin order' for x in pending)
oid=next(x['id'] for x in adminorders if x['equipment_id']==eid and x['description']=='admin order')
assert call(f'/equipment/orders/{oid}/costs',token=w)['code']!=200
print('worker scope, technician pending queue, administrator scope and costs verified')
assert call(f'/equipment/orders/{oid}',token=w)['code']!=200
assert call(f'/equipment/orders/{oid}',token=tech)['code']==200
assert call(f'/equipment/orders/{oid}',token=a)['code']==200
print('detail access scope verified')
detail=call(f'/equipment/orders/{oid}',token=a)
assert [(x['from_status'],x['to_status']) for x in detail['data']['transitions']]==[('NEW','REPORTED')]
print('direct report creation log verified')
