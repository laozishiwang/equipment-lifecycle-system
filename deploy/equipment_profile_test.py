import json,urllib.request,uuid
base='http://127.0.0.1:18090/prod-api'
def call(path,method='GET',data=None,token=None):
 h={'Content-Type':'application/json'}
 if token:h['Authorization']='Bearer '+token
 with urllib.request.urlopen(urllib.request.Request(base+path,None if data is None else json.dumps(data).encode(),h,method=method),timeout=15) as r:return json.load(r)
t=call('/login','POST',{'username':'admin','password':'admin123'})['token']
assert call('/equipment/assets/1',token=t)['code']==200
code='PROFILE-'+uuid.uuid4().hex[:10];data={'code':code,'name':'profile test','manufacturer':'Maker A','serialNumber':'SER123','purchaseDate':'2025-01-01','warrantyUntil':'2027-01-01'}
assert call('/equipment/assets','POST',data,t)['code']==200
eid=next(x['id'] for x in call('/equipment/assets?keyword='+code,token=t)['data'] if x['code']==code)
detail=call(f'/equipment/assets/{eid}',token=t)['data'];assert detail['manufacturer']=='Maker A' and detail['serial_number']=='SER123' and detail['purchase_date']=='2025-01-01'
edit={'name':'profile test','status':'ACTIVE','manufacturer':'Maker B','serialNumber':'SER123','purchaseDate':'2025-01-01','warrantyUntil':'2027-01-01'}
assert call(f'/equipment/assets/{eid}','PUT',edit,t)['code']==200
assert call(f'/equipment/assets/{eid}',token=t)['data']['manufacturer']=='Maker B'
edit['warrantyUntil']='2024-01-01';assert call(f'/equipment/assets/{eid}','PUT',edit,t)['code']!=200
print('old equipment compatibility, profile create/edit and date validation passed')
