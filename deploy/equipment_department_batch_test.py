"""Isolated test for atomic, conflict-safe department assignment."""
import concurrent.futures
import json
import urllib.error
import urllib.request
import uuid

BASE='http://127.0.0.1:18090/prod-api'
def call(path,method='GET',data=None,token=None):
    headers={'Content-Type':'application/json'}
    if token: headers['Authorization']='Bearer '+token
    request=urllib.request.Request(BASE+path,None if data is None else json.dumps(data).encode(),headers,method=method)
    try:
        with urllib.request.urlopen(request,timeout=30) as response:return json.load(response)
    except urllib.error.HTTPError as error:return {'code':error.code}

admin=call('/login','POST',{'username':'admin','password':'admin123'})['token']
worker=call('/login','POST',{'username':'role_worker_test','password':'admin123'})['token']
choices=call('/equipment/assets/departments',token=admin)['data']
assert len(choices)>=2
dept1,dept2=choices[0]['dept_id'],choices[1]['dept_id']
tag='BATCH-'+uuid.uuid4().hex[:8]
for i in range(4): assert call('/equipment/assets','POST',{'code':f'{tag}-{i}','name':'batch department test'},admin)['code']==200
assets=call('/equipment/assets?keyword='+tag,token=admin)['data']
ids=sorted(row['id'] for row in assets)
assert len(ids)==4
endpoint='/equipment/assets/departments/batch'
def assign(user,department,items):return call(endpoint,'POST',{'deptId':department,'equipmentIds':items},user)
def detail(asset):return call(f'/equipment/assets/{asset}/department',token=admin)['data']
assert assign(worker,dept1,ids[:2])['code']!=200
assert assign(admin,dept1,[ids[0],ids[0]])['code']!=200
assert assign(admin,999999999999,ids[:2])['code']!=200
assert assign(admin,dept1,ids[:2])['data']['assigned']==2
assert assign(admin,dept2,[ids[0],ids[2]])['code']!=200
assert detail(ids[2])['current']==[] and detail(ids[2])['history']==[]
assert assign(admin,dept1,[ids[2],999999999999])['code']!=200
with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
    results=list(pool.map(lambda department:assign(admin,department,ids[2:]),[dept1,dept2]))
assert sum(result.get('code')==200 for result in results)==1,results
final=[detail(asset) for asset in ids[2:]]
assert all(len(row['current'])==1 and len(row['history'])==1 for row in final)
assert final[0]['current'][0]['dept_id']==final[1]['current'][0]['dept_id']
print('batch ownership permissions, conflict atomicity, invalid data and concurrent assignment passed')
