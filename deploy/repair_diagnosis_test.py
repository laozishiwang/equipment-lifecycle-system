import datetime,json,urllib.request,urllib.error,uuid
from decimal import Decimal
import io,zipfile
from urllib.parse import urlencode
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
codeValue='FC-'+uuid.uuid4().hex[:12];catalog={'code':codeValue,'category':'mechanical-'+codeValue,'part':'bearing','symptom':'noise'}
faultId=call('/equipment/fault-codes','POST',catalog,a)['data']['id']
date=datetime.date.today().isoformat();repair={'repairDate':date,'description':'first repair','diagnosis':'bearing wear','faultCategory':'MECHANICAL','faultCodeId':faultId,'costs':[{'category':'LABOR','description':'labor','amount':10}]}
assert call(f'/equipment/orders/{oid}/complete','POST',{**repair,'diagnosis':'x'*2001},t)['code']!=200
assert call(f'/equipment/orders/{oid}/complete','POST',{**repair,'faultCategory':'INVALID'},t)['code']!=200
assert call(f'/equipment/orders/{oid}/complete','POST',repair,other)['code']!=200
assert call(f'/equipment/orders/{oid}/complete','POST',repair,t)['code']==200
assert call('/equipment/fault-codes/'+str(faultId),'PUT',{**catalog,'symptom':'changed'},a)['code']==200
assert call(f'/equipment/orders/{oid}/trial','POST',{'result':'PASS'},other)['code']!=200
assert call(f'/equipment/orders/{oid}/trial','POST',{'result':'FAIL','notes':''},t)['code']!=200
assert call(f'/equipment/orders/{oid}/close','POST',{},d)['code']!=200
assert call(f'/equipment/orders/{oid}/trial','POST',{'result':'FAIL','notes':'still faulty'},t)['code']==200
assert call(f'/equipment/orders/{oid}',token=a)['data']['status']=='ARRIVED'
repair={'repairDate':date,'description':'second repair','diagnosis':'sensor fault','faultCategory':'CONTROL','costs':[{'category':'PARTS','description':'part','amount':5}]}
assert call(f'/equipment/orders/{oid}/complete','POST',repair,t)['code']==200
assert call(f'/equipment/orders/{oid}/trial','POST',{'result':'PASS','notes':'verified'},t)['code']==200
assert call(f'/equipment/orders/{oid}/close','POST',{},d)['code']==200
detail=call(f'/equipment/orders/{oid}',token=a)['data'];assert [x['description'] for x in detail['repairs']]==['first repair','second repair']
assert [x['diagnosis'] for x in detail['repairs']]==['bearing wear','sensor fault']
assert [x['fault_category'] for x in detail['repairs']]==['MECHANICAL','CONTROL']
assert detail['repairs'][0]['fault_code']==codeValue and detail['repairs'][0]['fault_symptom']=='noise'
assert call(f'/equipment/orders/{oid}',token=other)['code']!=200
assert [x['result'] for x in detail['trials']]==['FAIL','PASS']
costs=call(f'/equipment/orders/{oid}/costs',token=a)['data'];assert sum(Decimal(str(x['amount'])) for x in costs)==Decimal('15')
assert call('/equipment/overview/faults',token=w)['code'] in (401,403)
faults=call('/equipment/overview/faults',token=a)['data']
assert any(x['code']==codeValue and x['symptom']=='noise' and int(x['repair_count'])==1 for x in faults)
filtered=call('/equipment/overview/faults?startDate='+date+'&endDate='+date,token=a)['data']
assert any(x['code']==codeValue for x in filtered)
assert call('/equipment/overview/faults?startDate=2020-01-01',token=a)['code']!=200
assert call('/equipment/overview/faults?startDate=2022-01-01&endDate=2020-01-01',token=a)['code']!=200
assert call('/equipment/overview/faults?startDate=2020-01-01&endDate=2022-01-01',token=a)['code']!=200
before=sum(int(x['repair_count']) for x in faults if x['code']==codeValue)
assert call('/equipment/orders','POST',{'equipmentId':eid,'description':'cancelled stats test'},w)['code']==200
cancelId=next(x['id'] for x in call('/equipment/orders',token=w)['data'] if x['equipment_id']==eid and x['description']=='cancelled stats test')
assert call(f'/equipment/orders/{cancelId}/accept','POST',{},t)['code']==200
assert call(f'/equipment/orders/{cancelId}/arrive','POST',{},t)['code']==200
assert call(f'/equipment/orders/{cancelId}/complete','POST',{'repairDate':date,'description':'cancelled repair','faultCodeId':faultId,'costs':[]},t)['code']==200
assert call(f'/equipment/orders/{cancelId}/cancel','POST',{'reason':'test'},d)['code']==200
later=call('/equipment/overview/faults',token=a)['data']
assert sum(int(x['repair_count']) for x in later if x['code']==codeValue)==before
params={'code':codeValue,'category':catalog['category'],'part':'bearing','symptom':'noise','startDate':date,'endDate':date}
path='/equipment/overview/faults/orders?'+urlencode(params)
assert call(path,token=w)['code'] in (401,403)
orders=call(path,token=a)['data'];assert [item['id'] for item in orders]==[oid]
assert call(path+'&beforeId='+str(oid),token=a)['data']==[]
assert call(path+'&beforeId=0',token=a)['code']!=200
exportPath='/equipment/overview/faults/export?startDate='+date+'&endDate='+date
assert call(exportPath,token=w)['code'] in (401,403)
request=urllib.request.Request(base+exportPath,headers={'Authorization':'Bearer '+a})
with urllib.request.urlopen(request,timeout=30) as response:
 assert response.headers.get_content_type()=='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
 data=response.read()
with zipfile.ZipFile(io.BytesIO(data)) as archive:
 xml=''.join(archive.read(name).decode('utf-8') for name in archive.namelist() if name.endswith('.xml'))
 assert codeValue in xml and '<f>' not in xml
print('repair diagnosis, statistics, xlsx export, drilldown and permissions passed')
