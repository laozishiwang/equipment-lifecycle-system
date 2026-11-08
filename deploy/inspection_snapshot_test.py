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
a=login('admin');w=login('role_worker_test');other=login('smoke_worker');code='SNAP-'+uuid.uuid4().hex[:8]
assert call('/equipment/assets',a,{'code':code,'name':'snapshot test'})['code']==200
id=next(x['id'] for x in call('/equipment/assets?keyword='+code,a)['data'] if x['code']==code)
path='/equipment/assets/'+str(id)+'/inspection-template'
t=call(path,a,{'name':'v1','items':[{'name':'oil','standard':'no leak'}]},'PUT')['data']['id']
def submit(template,items):return call('/equipment/inspections',w,{'equipmentId':id,'result':'NORMAL','templateId':template,'items':items})
assert submit(None,[{'name':'oil','result':'NORMAL'}])['code']!=200
assert submit(t,[])['code']!=200
assert submit(t,[{'name':'changed','result':'NORMAL'}])['code']!=200
r=submit(t,[{'name':'oil','result':'NORMAL'},{'name':'extra','result':'NORMAL'}]);assert r['code']==200
inspection=r['data']['inspectionId']
t2=call(path,a,{'name':'v2','items':[{'name':'oil','standard':'new rule'}]},'PUT')['data']['id'];assert t2!=t
assert submit(t,[{'name':'oil','result':'NORMAL'}])['code']!=200
snap=call('/equipment/inspections/'+str(inspection)+'/template-snapshot',w)['data'];assert len(snap)==1 and snap[0]['template_name']=='v1' and snap[0]['standard_text']=='no leak'
assert call('/equipment/inspections/'+str(inspection)+'/template-snapshot',other)['code']!=200
print('template version mismatch, required items, historical standard and scope passed')
