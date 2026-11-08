import json,urllib.request,urllib.error,uuid
base='http://127.0.0.1:18090/prod-api'
def call(path,method='GET',data=None,token=None):
 h={'Content-Type':'application/json'}
 if token:h['Authorization']='Bearer '+token
 try:
  with urllib.request.urlopen(urllib.request.Request(base+path,None if data is None else json.dumps(data).encode(),h,method=method),timeout=30) as r:return json.load(r)
 except urllib.error.HTTPError as e:return {'code':e.code}
def login(n):return call('/login','POST',{'username':n,'password':'admin123'})['token']
a=login('admin');w=login('role_worker_test');t=login('role_tech_test');code='TEST-'+uuid.uuid4().hex[:12];v={'code':code,'category':'test-'+code,'part':'bearing','symptom':'noise'}
assert call('/equipment/fault-codes','POST',v,w)['code']!=200
r=call('/equipment/fault-codes','POST',v,a);assert r['code']==200,r
id=r['data']['id'];assert call('/equipment/fault-codes/'+str(id),'PUT',{**v,'symptom':'changed'},a)['code']==200
assert call('/equipment/fault-codes/'+str(id),'PUT',v,w)['code']!=200
assert call('/equipment/fault-codes','POST',v,a)['code']!=200
assert any(x['id']==id for x in call('/equipment/fault-codes',token=t)['data'])
assert call('/equipment/fault-codes/'+str(id)+'/status','PUT',{'status':'INACTIVE'},a)['code']==200
assert all(x['id']!=id for x in call('/equipment/fault-codes',token=t)['data'])
assert call('/equipment/fault-codes?all=true',token=t)['code']!=200
assert any(x['id']==id for x in call('/equipment/fault-codes?all=true',token=a)['data'])
assert call('/equipment/fault-codes/'+str(id)+'/status','PUT',{'status':None},a)['code']!=200
print('catalog creation, duplicate protection, role access and deactivation passed')
