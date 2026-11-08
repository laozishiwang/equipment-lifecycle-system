import datetime,json,urllib.request,urllib.error,uuid,subprocess
from decimal import Decimal
base='http://127.0.0.1:18090/prod-api'
def call(path,method='GET',data=None,token=None):
 h={'Content-Type':'application/json'}
 if token:h['Authorization']='Bearer '+token
 req=urllib.request.Request(base+path,None if data is None else json.dumps(data).encode(),h,method=method)
 try:
  with urllib.request.urlopen(req,timeout=20) as r:return json.load(r)
 except urllib.error.HTTPError as e:return {'code':e.code}
def login(name):return call('/login','POST',{'username':name,'password':'admin123'})['token']
a=login('admin');w=login('role_worker_test');t=login('role_tech_test');other=login('smoke_tech_b');d=login('role_director_test');code='TRIAL-'+uuid.uuid4().hex[:10]
assert call('/equipment/assets','POST',{'code':code,'name':'trial test'},a)['code']==200
eid=next(x['id'] for x in call('/equipment/assets?keyword='+code,token=a)['data'] if x['code']==code)
assert call('/equipment/orders','POST',{'equipmentId':eid,'description':'test'},w)['code']==200
oid=next(x['id'] for x in call('/equipment/orders',token=w)['data'] if x['equipment_id']==eid)
assert call(f'/equipment/orders/{oid}/accept','POST',{},t)['code']==200
assert call(f'/equipment/orders/{oid}/arrive','POST',{},t)['code']==200
date=datetime.date.today().isoformat();repair={'repairDate':date,'description':'first repair','costs':[{'category':'LABOR','description':'labor','amount':10}]}
assert call(f'/equipment/orders/{oid}/complete','POST',repair,t)['code']==200
assert call(f'/equipment/orders/{oid}/trial','POST',{'result':'PASS'},other)['code']!=200
assert call(f'/equipment/orders/{oid}/trial','POST',{'result':'FAIL','notes':''},t)['code']!=200
assert call(f'/equipment/orders/{oid}/close','POST',{},d)['code']!=200
assert call(f'/equipment/orders/{oid}/trial','POST',{'result':'FAIL','notes':'still faulty'},t)['code']==200
assert call(f'/equipment/orders/{oid}',token=a)['data']['status']=='ARRIVED'
def sql(statement):
 p=subprocess.run(['docker','exec','-i','equipment-rebuild-mysql-1','sh','-c','mysql -uroot -p"$MYSQL_ROOT_PASSWORD" equipment_dev 2>/dev/null'],input=statement.encode(),capture_output=True);assert p.returncode==0
# Deliberately corrupt only the test order to verify the closure guard.
sql(f"UPDATE ems_work_order SET status='COMPLETED' WHERE id={oid}")
assert call(f'/equipment/orders/{oid}/close','POST',{},d)['code']!=200
sql(f"UPDATE ems_work_order SET status='ARRIVED' WHERE id={oid}")
repair={'repairDate':date,'description':'second repair','costs':[{'category':'PARTS','description':'part','amount':5}]}
assert call(f'/equipment/orders/{oid}/complete','POST',repair,t)['code']==200
assert call(f'/equipment/orders/{oid}/trial','POST',{'result':'PASS','notes':'verified'},t)['code']==200
assert call(f'/equipment/orders/{oid}/close','POST',{},d)['code']==200
detail=call(f'/equipment/orders/{oid}',token=a)['data'];assert [x['description'] for x in detail['repairs']]==['first repair','second repair']
assert [x['result'] for x in detail['trials']]==['FAIL','PASS']
costs=call(f'/equipment/orders/{oid}/costs',token=a)['data'];assert sum(Decimal(str(x['amount'])) for x in costs)==Decimal('15')
assert call('/equipment/orders','POST',{'equipmentId':eid,'description':'legacy compatibility test'},w)['code']==200
legacy=next(x['id'] for x in call('/equipment/orders',token=w)['data'] if x['equipment_id']==eid and x['description']=='legacy compatibility test')
sql(f"UPDATE ems_work_order SET status='COMPLETED' WHERE id={legacy}")
assert call(f'/equipment/orders/{legacy}/close','POST',{},d)['code']==200
print('closure guard, rework, legacy compatibility and permissions passed')
