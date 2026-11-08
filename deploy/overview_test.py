import datetime,json,urllib.request,urllib.error,uuid
from decimal import Decimal
base='http://127.0.0.1:18090/prod-api'
def call(path,method='GET',data=None,token=None):
 h={'Content-Type':'application/json'}
 if token:h['Authorization']='Bearer '+token
 req=urllib.request.Request(base+path,None if data is None else json.dumps(data).encode(),h,method=method)
 try:
  with urllib.request.urlopen(req,timeout=15) as r:return json.load(r)
 except urllib.error.HTTPError as e:return {'code':e.code}
def login(user):return call('/login','POST',{'username':user,'password':'admin123'})['token']
a=login('admin');w=login('role_worker_test');d=login('role_director_test')
assert call('/equipment/overview',token=w)['code'] in (401,403)
assert call('/equipment/overview',token=d)['code']==200
before=call('/equipment/overview',token=a)['data'];code='STAT-'+uuid.uuid4().hex[:10]
assert call('/equipment/assets','POST',{'code':code,'name':'stats test'},a)['code']==200
eid=next(x['id'] for x in call('/equipment/assets?keyword='+code,token=a)['data'] if x['code']==code)
assert call('/equipment/orders','POST',{'equipmentId':eid,'description':'stats test'},a)['code']==200
oid=next(x['id'] for x in call('/equipment/orders',token=a)['data'] if x['equipment_id']==eid)
assert call(f'/equipment/orders/{oid}/accept','POST',{},a)['code']==200
assert call(f'/equipment/orders/{oid}/arrive','POST',{},a)['code']==200
assert call(f'/equipment/orders/{oid}/complete','POST',{'repairDate':datetime.date.today().isoformat(),'description':'test','costs':[{'category':'LABOR','description':'test','amount':12.34},{'category':'PARTS','description':'test','amount':5.67}]},a)['code']==200
assert call(f'/equipment/orders/{oid}/trial','POST',{'result':'PASS','notes':'ok'},a)['code']==200
after=call('/equipment/overview',token=a)['data']
assert int(after['equipment']['total'])==int(before['equipment']['total'])+1
assert int(after['orders']['completed'])==int(before['orders']['completed'])+1
assert Decimal(str(after['costs']['labor']))-Decimal(str(before['costs']['labor']))==Decimal('12.34')
assert Decimal(str(after['costs']['parts']))-Decimal(str(before['costs']['parts']))==Decimal('5.67')
print('overview counts, categorized costs and permissions verified')


