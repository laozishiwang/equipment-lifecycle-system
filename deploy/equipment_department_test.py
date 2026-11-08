"""Isolated integration test for optional equipment ownership metadata."""
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
        with urllib.request.urlopen(request,timeout=20) as response:return json.load(response)
    except urllib.error.HTTPError as error:return {'code':error.code}

admin=call('/login','POST',{'username':'admin','password':'admin123'})['token']
worker=call('/login','POST',{'username':'role_worker_test','password':'admin123'})['token']
code='DEPT-'+uuid.uuid4().hex[:10]
assert call('/equipment/assets','POST',{'code':code,'name':'department test'},admin)['code']==200
asset=next(row['id'] for row in call('/equipment/assets?keyword='+code,token=admin)['data'] if row['code']==code)
base=f'/equipment/assets/{asset}/department'
choices=call('/equipment/assets/departments',token=admin)['data']
assert len(choices)>=2
a,b=choices[0],choices[1]
assert call(base,token=admin)['data']['current']==[]
assert call(base,'PUT',{},admin)['code']!=200
assert call(base,'PUT',{'deptId':999999999999},admin)['code']!=200
assert call(base,'PUT',{'deptId':a['dept_id']},worker)['code']!=200
assert call(base,'PUT',{'deptId':a['dept_id']},admin)['code']==200
assert call(base,'PUT',{'deptId':a['dept_id']},admin)['code']==200
result=call(base,token=admin)['data']
assert result['current'][0]['dept_id']==a['dept_id'] and len(result['history'])==1
assigned=call('/equipment/assets?ownership=ASSIGNED&keyword='+code,token=worker)['data']
assert len(assigned)==1 and assigned[0]['dept_id']==a['dept_id'] and assigned[0]['dept_name']==a['dept_name']
assert call('/equipment/assets?ownership=UNASSIGNED&keyword='+code,token=admin)['data']==[]
assert call('/equipment/assets?ownership=INVALID',token=admin)['code']!=200
assert call('/equipment/assets?ownership=ASSIGNED&keyword='+code+'&beforeId='+str(asset),token=admin)['data']==[]
assert call(f'/equipment/assets/{asset}','PUT',{'name':'legacy edit','status':'ACTIVE'},admin)['code']==200
assert call(base,token=admin)['data']['current'][0]['dept_id']==a['dept_id']
assert call(base,'PUT',{'deptId':b['dept_id']},admin)['code']==200
assert call(base,'PUT',{'clear':True},admin)['code']==200
result=call(base,token=admin)['data']
assert result['current']==[] and len(result['history'])==3
assert len(call('/equipment/assets?ownership=UNASSIGNED&keyword='+code,token=admin)['data'])==1
assert call('/equipment/assets?ownership=ASSIGNED&keyword='+code,token=admin)['data']==[]
assert result['history'][1]['old_dept_name']==a['dept_name'] and result['history'][1]['new_dept_name']==b['dept_name']
print('optional department ownership, history, explicit clear, permissions and legacy edit passed')
