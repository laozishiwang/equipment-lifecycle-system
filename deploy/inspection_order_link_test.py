import json, urllib.request, urllib.error, uuid

base = 'http://127.0.0.1:18090/prod-api'
def call(path, token=None, data=None):
    headers = {'Content-Type': 'application/json'}
    if token: headers['Authorization'] = 'Bearer ' + token
    req = urllib.request.Request(base + path, None if data is None else json.dumps(data).encode(), headers, method='GET' if data is None else 'POST')
    try:
        with urllib.request.urlopen(req, timeout=20) as response: return json.load(response)
    except urllib.error.HTTPError as error: return {'code': error.code}
def login(name): return call('/login', data={'username':name, 'password':'admin123'})['token']
worker, other, admin, tech = (login(name) for name in ('role_worker_test', 'smoke_worker', 'admin', 'role_tech_test'))
remark = 'LINK-' + uuid.uuid4().hex[:10]
created = call('/equipment/inspections', worker, {'equipmentId':1, 'result':'ABNORMAL', 'remark':remark, 'createOrder':True})
assert created['code'] == 200, created
inspection, order = created['data']['inspectionId'], created['data']['orderId']
def record(token): return next(row for row in call('/equipment/inspections', token)['data'] if row['id'] == inspection)
assert record(worker)['order_id'] == order and record(worker)['order_status'] == 'REPORTED'
assert record(admin)['order_id'] == order
assert not any(row['id'] == inspection for row in call('/equipment/inspections', other)['data'])
assert call(f'/equipment/orders/{order}/accept', tech, {})['code'] == 200
assert record(worker)['order_status'] == 'ACCEPTED'
assert call(f'/equipment/orders/{order}', worker)['data']['status'] == 'ACCEPTED'
normal = call('/equipment/inspections', worker, {'equipmentId':1, 'result':'NORMAL'})['data']['inspectionId']
assert next(row for row in call('/equipment/inspections', worker)['data'] if row['id'] == normal)['order_id'] is None
print('inspection order link, status refresh, visibility and normal inspection passed')
