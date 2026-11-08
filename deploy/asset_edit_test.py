import json, urllib.request, uuid
base='http://127.0.0.1:18090/prod-api'
def call(path,method='GET',data=None,token=None):
 h={'Content-Type':'application/json'}
 if token:h['Authorization']='Bearer '+token
 with urllib.request.urlopen(urllib.request.Request(base+path,None if data is None else json.dumps(data).encode(),h,method=method),timeout=15) as r:return json.load(r)
t=call('/login','POST',{'username':'admin','password':'admin123'})['token']; code='EDIT-'+uuid.uuid4().hex[:10]
assert call('/equipment/assets','POST',{'code':code,'name':'edit test'},t)['code']==200
eid=next(x['id'] for x in call('/equipment/assets',token=t)['data'] if x['code']==code)
assert call('/equipment/orders','POST',{'equipmentId':eid,'description':'open order'},t)['code']==200
retire={'name':'edited','model':'x','location':'test','status':'RETIRED'}
assert call(f'/equipment/assets/{eid}','PUT',retire,t)['code']!=200
retire['status']='ACTIVE'; assert call(f'/equipment/assets/{eid}','PUT',retire,t)['code']==200
print('edit allowed; retirement with open order denied')
