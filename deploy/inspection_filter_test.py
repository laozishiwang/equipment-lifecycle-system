import json,urllib.request,urllib.error,uuid
base='http://127.0.0.1:18090/prod-api'; tag='INSPFILTER-'+uuid.uuid4().hex[:10]
def call(path,token=None,data=None):
 h={'Content-Type':'application/json'}
 if token:h['Authorization']='Bearer '+token
 req=urllib.request.Request(base+path,None if data is None else json.dumps(data).encode(),h,method='GET' if data is None else 'POST')
 try:
  with urllib.request.urlopen(req,timeout=20) as r:return json.load(r)
 except urllib.error.HTTPError as e:return {'code':e.code}
def login(name):return call('/login',data={'username':name,'password':'admin123'})['token']
w=login('role_worker_test');a=login('admin')
for token,result,suffix in [(w,'NORMAL','own-normal'),(w,'ABNORMAL','own-abnormal'),(a,'ABNORMAL','other-abnormal')]:
 assert call('/equipment/inspections',token,{'equipmentId':1,'result':result,'remark':tag+'-'+suffix})['code']==200
for result,suffix in [('NORMAL','own-normal'),('ABNORMAL','own-abnormal')]:
 rows=call('/equipment/inspections?result='+result,w)['data'];assert rows and all(x['result']==result for x in rows)
 assert any(x['remark']==tag+'-'+suffix for x in rows)
 assert not any(x['remark']==tag+'-other-abnormal' for x in rows)
admin=call('/equipment/inspections?result=ABNORMAL',a)['data'];assert any(x['remark']==tag+'-other-abnormal' for x in admin)
cursor=admin[0]['id'];second=call('/equipment/inspections?result=ABNORMAL&beforeId='+str(cursor),a)['data'];assert all(x['id']<cursor and x['result']=='ABNORMAL' for x in second)
assert call('/equipment/inspections?result=INVALID',w)['code']!=200
print('inspection result filtering, cursor, invalid input and role scope passed')
