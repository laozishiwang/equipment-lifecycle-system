import concurrent.futures, json, threading, urllib.error, urllib.request, uuid

base = 'http://127.0.0.1:18090/prod-api'
def call(path, token=None, data=None):
    headers = {'Content-Type':'application/json'}
    if token: headers['Authorization'] = 'Bearer ' + token
    request = urllib.request.Request(base+path, None if data is None else json.dumps(data).encode(), headers, method='GET' if data is None else 'POST')
    try:
        with urllib.request.urlopen(request, timeout=30) as response: return json.load(response)
    except urllib.error.HTTPError as error: return {'code':error.code}
def login(name): return call('/login', data={'username':name,'password':'admin123'})['token']
worker, other, admin = (login(name) for name in ('role_worker_test','smoke_worker','admin'))
def inspection(result):
    answer=call('/equipment/inspections',worker,{'equipmentId':1,'result':result,'remark':'deferred-'+uuid.uuid4().hex[:8]})
    assert answer['code']==200, answer
    return answer['data']['inspectionId']
normal=inspection('NORMAL'); abnormal=inspection('ABNORMAL')
def convert(id, token, description='漏油'):
    return call(f'/equipment/inspections/{id}/work-order',token,{'description':description})
assert convert(normal,worker)['code'] != 200
assert convert(abnormal,other)['code'] != 200
assert convert(abnormal,worker,'   ')['code'] != 200
assert convert(abnormal,worker,'x'*2001)['code'] != 200
barrier=threading.Barrier(2)
def race(_):
    barrier.wait()
    return convert(abnormal,worker)
with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
    results=list(pool.map(race,range(2)))
assert sum(r.get('code')==200 for r in results)==1,results
order=next(r['data']['orderId'] for r in results if r.get('code')==200)
assert convert(abnormal,admin)['code'] != 200
row=next(x for x in call('/equipment/inspections',worker)['data'] if x['id']==abnormal)
assert row['order_id']==order and row['order_status']=='REPORTED'
detail=call(f'/equipment/orders/{order}',worker)['data']
assert detail['description']=='漏油'
assert [(x['from_status'],x['to_status']) for x in detail['transitions']]==[('NEW','REPORTED')]
print('deferred conversion: permissions, validation, concurrency, linkage and audit passed')
