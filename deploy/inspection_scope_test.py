import json,urllib.request,urllib.parse,uuid
base='http://127.0.0.1:18090/prod-api'
def call(path,method='GET',data=None,token=None):
 h={'Content-Type':'application/json'}
 if token:h['Authorization']='Bearer '+token
 with urllib.request.urlopen(urllib.request.Request(base+path,None if data is None else json.dumps(data).encode(),h,method=method),timeout=15) as r:return json.load(r)
def login(user):return call('/login','POST',{'username':user,'password':'admin123'})['token']
a=login('admin');w=login('smoke_worker');code='FIND-'+uuid.uuid4().hex[:10]
assert call('/equipment/assets','POST',{'code':code,'name':'search test'},a)['code']==200
rows=call('/equipment/assets?keyword='+urllib.parse.quote(code),token=a)['data'];assert len(rows)==1 and rows[0]['code']==code
eid=rows[0]['id']
assert call('/equipment/inspections','POST',{'equipmentId':eid,'result':'NORMAL','remark':'admin record','createOrder':False},a)['code']==200
assert call('/equipment/inspections','POST',{'equipmentId':eid,'result':'NORMAL','remark':'worker record','createOrder':False},w)['code']==200
mine=call('/equipment/inspections',token=w)['data'];allrows=call('/equipment/inspections',token=a)['data']
assert any(x['equipment_id']==eid and x['remark']=='worker record' for x in mine)
assert not any(x['equipment_id']==eid and x['remark']=='admin record' for x in mine)
assert any(x['equipment_id']==eid and x['remark']=='admin record' for x in allrows)
assert call('/equipment/assets?keyword=%25',token=a)['data']==[]
print('device search, literal wildcard and inspection data scope verified')
