#!/usr/bin/env python3
"""Isolated HTTP acceptance test. Requires scope enabled and pre-provisioned roles.

Set EMS_ISOLATED_FIXTURE=YES, EMS_TEST_ADMIN_USER/PASSWORD,
EMS_TEST_A_USER/PASSWORD, EMS_TEST_DEPT_A, EMS_TEST_DEPT_B, and four distinct
pre-created unassigned fixture IDs EMS_TEST_DEVICE_1 through EMS_TEST_DEVICE_4.
User A must have asset:edit restricted to A; administrator must access both.
This test changes ownership of those synthetic devices and leaves them assigned.
Never point the development port at production.
"""
import json
import os
import urllib.error
import urllib.request

BASE = 'http://127.0.0.1:18090/prod-api'
if os.environ.get('EMS_ISOLATED_FIXTURE') != 'YES':
    raise SystemExit('Refusing to run without EMS_ISOLATED_FIXTURE=YES')
if any(k in os.environ for k in ('EMS_BASE_URL','BASE_URL','HTTP_PROXY','HTTPS_PROXY','ALL_PROXY')):
    raise SystemExit('Refusing configurable target or proxy')

def required(name):
    value=os.environ.get(name)
    if not value: raise SystemExit('Missing '+name)
    return value

def call(path, method='GET', body=None, token=None):
    request=urllib.request.Request(BASE+path, None if body is None else json.dumps(body).encode(),
        {'Content-Type':'application/json',**({'Authorization':'Bearer '+token} if token else {})}, method=method)
    try:
        with urllib.request.build_opener(urllib.request.ProxyHandler({})).open(request,timeout=20) as response:
            return json.load(response)
    except urllib.error.HTTPError as exc:
        return {'code':exc.code}

def login(prefix):
    result=call('/login','POST',{'username':required(prefix+'_USER'),'password':required(prefix+'_PASSWORD')})
    if 'token' not in result: raise AssertionError('login failed for '+prefix)
    return result['token']

def ok(result):
    if result.get('code')!=200: raise AssertionError(result)
    return result

def denied(result):
    if result.get('code')==200: raise AssertionError('unexpected permission grant')

def get_owner(token,device):
    result=ok(call('/equipment/assets/%d/department'%device,token=token))
    rows=result['data']['current']
    return None if not rows else int(rows[0]['dept_id'])

def assign(token,device,department):
    return call('/equipment/assets/%d/department'%device,'PUT',{'deptId':department},token)

admin=login('EMS_TEST_ADMIN'); user=login('EMS_TEST_A')
a=int(required('EMS_TEST_DEPT_A')); b=int(required('EMS_TEST_DEPT_B'))
if a<=0 or b<=0 or a==b: raise SystemExit('Need distinct positive A/B department IDs')
ids=[int(required('EMS_TEST_DEVICE_'+str(i))) for i in range(1,5)]
if any(i<=0 for i in ids) or len(set(ids))!=4:
    raise SystemExit('Need four distinct positive unassigned fixture IDs')
for device in ids:
    if get_owner(admin,device) is not None:
        raise SystemExit('Fixture must exist and be unassigned: '+str(device))
ea,eb,empty,extra=ids
ok(assign(admin,ea,a)); ok(assign(admin,eb,b))
assert get_owner(user,ea)==a
# Source B and unassigned devices cannot be read or captured by A.
denied(call('/equipment/assets/%d/department'%eb,token=user))
denied(assign(user,eb,a)); denied(assign(user,empty,a))
# A must not transfer its own device to B or clear its ownership.
denied(assign(user,ea,b))
denied(call('/equipment/assets/%d/department'%ea,'PUT',{'clear':True},user))
assert get_owner(admin,ea)==a and get_owner(admin,eb)==b and get_owner(admin,empty) is None
# Admin batch including an assigned device must fail without partially assigning the rest.
denied(call('/equipment/assets/departments/batch','POST',{'deptId':a,'equipmentIds':[empty,ea,extra]},admin))
assert get_owner(admin,empty) is None and get_owner(admin,extra) is None and get_owner(admin,ea)==a
# A cannot bulk-claim unassigned equipment; administrator can.
denied(call('/equipment/assets/departments/batch','POST',{'deptId':a,'equipmentIds':[empty,extra]},user))
assert get_owner(admin,empty) is None and get_owner(admin,extra) is None
ok(call('/equipment/assets/departments/batch','POST',{'deptId':a,'equipmentIds':[empty,extra]},admin))
assert get_owner(admin,empty)==a and get_owner(admin,extra)==a
print('isolated department A/B source and destination, unassigned, batch atomicity passed; fixtures:',ids)
