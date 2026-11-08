import json, urllib.request, urllib.error, uuid, datetime
base='http://127.0.0.1:18090/prod-api'
def call(path,method='GET',data=None,token=None):
 h={'Content-Type':'application/json'}
 if token:h['Authorization']='Bearer '+token
 req=urllib.request.Request(base+path,None if data is None else json.dumps(data).encode(),h,method=method)
 try:
  with urllib.request.urlopen(req,timeout=15) as res:return json.load(res)
 except urllib.error.HTTPError as e:return {'code':e.code}
def login(user):
 result=call('/login','POST',{'username':user,'password':'admin123'}); assert result.get('token'); return result['token']
admin=login('admin'); a=login('smoke_tech_a'); b=login('smoke_tech_b')
code='OWN-'+uuid.uuid4().hex[:10]
assert call('/equipment/assets','POST',{'code':code,'name':'ownership test'},admin)['code']==200
assets=call('/equipment/assets',token=admin)['data']; eid=next(x['id'] for x in assets if x['code']==code)
assert call('/equipment/orders','POST',{'equipmentId':eid,'description':'ownership test'},admin)['code']==200
orders=call('/equipment/orders',token=admin)['data']; oid=next(x['id'] for x in orders if x['equipment_id']==eid)
assert call(f'/equipment/orders/{oid}/accept','POST',{},a)['code']==200
assert call(f'/equipment/orders/{oid}/arrive','POST',{},b)['code']!=200
assert call(f'/equipment/orders/{oid}/arrive','POST',{},a)['code']==200
completion={'repairDate':'2026-11-02','description':'test','costs':[]}
assert call(f'/equipment/orders/{oid}/complete','POST',completion,b)['code']!=200
future=dict(completion,repairDate=(datetime.date.today()+datetime.timedelta(days=1)).isoformat())
assert call(f'/equipment/orders/{oid}/complete','POST',future,a)['code']!=200
assert call(f'/equipment/orders/{oid}/complete','POST',completion,a)['code']==200
print('non-owner denied; assigned technician completed successfully')


