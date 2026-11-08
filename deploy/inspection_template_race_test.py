import concurrent.futures,json,threading,urllib.request,urllib.error,uuid
base='http://127.0.0.1:18090/prod-api'
def call(path,token=None,data=None,method=None):
 h={'Content-Type':'application/json'}
 if token:h['Authorization']='Bearer '+token
 req=urllib.request.Request(base+path,None if data is None else json.dumps(data).encode(),h,method=method or ('GET' if data is None else 'POST'))
 try:
  with urllib.request.urlopen(req,timeout=30) as r:return json.load(r)
 except urllib.error.HTTPError as e:return {'code':e.code}
a=call('/login',data={'username':'admin','password':'admin123'})['token']
w=call('/login',data={'username':'role_worker_test','password':'admin123'})['token']
code='TMPRACE-'+uuid.uuid4().hex[:10]
assert call('/equipment/assets',a,{'code':code,'name':'template race'})['code']==200
eid=next(x['id'] for x in call('/equipment/assets?keyword='+code,a)['data'] if x['code']==code)
path=f'/equipment/assets/{eid}/inspection-template'
for i in range(10):
 old=call(path,a,{'name':'old','items':[{'name':'oil','standard':'old rule'}]},'PUT');assert old['code']==200,old
 barrier=threading.Barrier(2)
 def submit():
  barrier.wait();return call('/equipment/inspections',w,{'equipmentId':eid,'result':'NORMAL','templateId':old['data']['id'],'items':[{'name':'oil','result':'NORMAL'}]})
 def change():
  barrier.wait();return call(path,a,{'name':'new','items':[{'name':'oil','standard':'new rule'}]},'PUT')
 with concurrent.futures.ThreadPoolExecutor(max_workers=2) as p:
  f=p.submit(submit);g=p.submit(change);result=f.result();updated=g.result()
 assert updated['code']==200,updated
 if result['code']==200:
  snap=call('/equipment/inspections/'+str(result['data']['inspectionId'])+'/template-snapshot',w)
  assert len(snap['data'])==1 and snap['data'][0]['template_name']=='old' and snap['data'][0]['standard_text']=='old rule',snap
 else: assert '模板' in result.get('msg',''),result
print('10 template update/submission races passed')
