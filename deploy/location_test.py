import json,urllib.request,uuid
base='http://127.0.0.1:18090/prod-api'
def call(path,method='GET',data=None,token=None):
 h={'Content-Type':'application/json'}
 if token:h['Authorization']='Bearer '+token
 with urllib.request.urlopen(urllib.request.Request(base+path,None if data is None else json.dumps(data).encode(),h,method=method),timeout=15) as r:return json.load(r)
t=call('/login','POST',{'username':'admin','password':'admin123'})['token'];code='LOC-'+uuid.uuid4().hex[:10]
assert call('/equipment/assets','POST',{'code':code,'name':'location test','location':'A'},t)['code']==200
eid=next(x['id'] for x in call('/equipment/assets',token=t)['data'] if x['code']==code)
assert call(f'/equipment/assets/{eid}','PUT',{'name':'location test','location':'B','status':'ACTIVE'},t)['code']==200
history=call(f'/equipment/assets/{eid}/history',token=t)['data'];assert [x['location'] for x in history['locations']]==['B','A']
print('initial and changed location history verified')
