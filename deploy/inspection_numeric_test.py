import json,urllib.request,urllib.error,uuid
base='http://127.0.0.1:18090/prod-api'
def call(path,token=None,data=None,method=None):
 h={'Content-Type':'application/json'}
 if token:h['Authorization']='Bearer '+token
 req=urllib.request.Request(base+path,None if data is None else json.dumps(data).encode(),h,method=method or ('GET' if data is None else 'POST'))
 try:
  with urllib.request.urlopen(req,timeout=20) as r:return json.load(r)
 except urllib.error.HTTPError as e:return {'code':e.code}
def login(n):return call('/login',data={'username':n,'password':'admin123'})['token']
a=login('admin');w=login('role_worker_test');other=login('smoke_worker');code='NUMBER-'+uuid.uuid4().hex[:8]
assert call('/equipment/assets',a,{'code':code,'name':'numeric test'})['code']==200
id=next(x['id'] for x in call('/equipment/assets?keyword='+code,a)['data'] if x['code']==code)
path='/equipment/assets/'+str(id)+'/inspection-template'
invalid={'name':'numeric','items':[{'name':'temperature','lowerBound':10,'upperBound':5}]}
assert call(path,a,invalid,'PUT')['code']!=200
payload={'name':'numeric','items':[{'name':'temperature','standard':'5 to 10','lowerBound':5,'upperBound':10,'unit':'C'}]}
t=call(path,a,payload,'PUT')['data']['id'];template=call(path,w)['data'];assert template['items'][0]['lower_bound']==5

def submit(value,item_result='NORMAL',overall='NORMAL'):
 return call('/equipment/inspections',w,{'equipmentId':id,'result':overall,'templateId':t,'items':[{'name':'temperature','result':item_result,'measuredValue':value}]})
assert submit(None)['code']!=200
assert submit(11)['code']!=200
assert submit(5)['code']==200
assert submit('5.0000')['code']==200
assert submit('5.00001')['code']!=200
assert submit('9999999999')['code']!=200
r=submit(11,'ABNORMAL','ABNORMAL');assert r['code']==200
inspection=r['data']['inspectionId']
assert call(path,a,{'name':'legacy','items':[{'name':'temperature'}]},'PUT')['code']!=200
assert call(path,a,{'name':'revised','ruleSchemaVersion':1,'items':[{'name':'temperature','lowerBound':0,'upperBound':20}]},'PUT')['code']==200
items=call('/equipment/inspections/'+str(inspection)+'/items',w)['data'];assert items[0]['measured_value']==11 and items[0]['upper_bound']==10 and items[0]['unit']=='C'
assert call('/equipment/inspections/'+str(inspection)+'/items',other)['code']!=200
print('numeric bounds, server verification, boundary, historical rule and permission passed')
