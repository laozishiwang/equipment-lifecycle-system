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
a=login('admin');w=login('role_worker_test');code='TMPL-'+uuid.uuid4().hex[:8]
assert call('/equipment/assets',a,{'code':code,'name':'template test'})['code']==200
id=next(x['id'] for x in call('/equipment/assets?keyword='+code,a)['data'] if x['code']==code)
path='/equipment/assets/'+str(id)+'/inspection-template';payload={'name':'test template','items':[{'name':'pressure','standard':'normal'},{'name':'leak','standard':'none'}]}
assert call(path,w,payload,'PUT')['code']!=200
assert call(path,a,{'name':'x','items':[]},'PUT')['code']!=200
assert call(path,a,payload,'PUT')['code']==200
r=call(path,w)['data'];assert r['name']==payload['name'] and [x['item_name'] for x in r['items']]==['pressure','leak']
assert call(path,a,{'name':'revised','items':[{'name':'temperature'}]},'PUT')['code']==200
r=call(path,w)['data'];assert r['name']=='revised' and len(r['items'])==1
print('template validation, equipment binding, ordering and role permissions passed')
