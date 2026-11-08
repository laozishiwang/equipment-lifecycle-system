import json, urllib.request, urllib.error, uuid, datetime, os
base=os.environ.get('PRODCHECK_BASE','http://127.0.0.1:18092/prod-api')
def call(path, method='GET', data=None, token=None):
    headers={'Content-Type':'application/json'}
    if token: headers['Authorization']='Bearer '+token
    req=urllib.request.Request(base+path, None if data is None else json.dumps(data).encode(), headers, method=method)
    try:
        with urllib.request.urlopen(req,timeout=15) as response: return json.load(response)
    except urllib.error.HTTPError as e: return {'error':e.code,'body':e.read().decode()[:200]}
login=call('/login','POST',{'username':'admin','password':os.environ.get('PRODCHECK_PASSWORD','Ems-Test-2026-OK!')})
print('login:',login.get('code'),login.get('msg'))
token=login.get('token')
if not token: raise SystemExit(1)
def check(name,result):
 print(name, result.get('code'), result.get('msg'))
 if result.get('code') != 200: raise SystemExit(1)
code='TEST-'+uuid.uuid4().hex[:12]
check('create equipment',call('/equipment/assets','POST',{'code':code,'name':'隔离测试设备','model':'test','location':'测试区'},token))
assets=call('/equipment/assets',token=token); check('list equipment',assets)
equipment=next(x['id'] for x in assets['data'] if x['code']==code)
check('inspection with report',call('/equipment/inspections','POST',{'equipmentId':equipment,'result':'ABNORMAL','remark':'隔离测试故障','createOrder':True},token))
orders=call('/equipment/orders',token=token);check('list orders',orders)
order=next(x['id'] for x in orders['data'] if x['equipment_id']==equipment)
check('accept',call(f'/equipment/orders/{order}/accept','POST',{},token))
check('arrive',call(f'/equipment/orders/{order}/arrive','POST',{},token))
check('complete',call(f'/equipment/orders/{order}/complete','POST',{'repairDate':datetime.date.today().isoformat(),'description':'更换零件','costs':[{'category':'LABOR','description':'人工','amount':50},{'category':'PARTS','description':'零件','amount':23.5}]},token))
costs=call(f'/equipment/orders/{order}/costs',token=token);check('costs',costs)
assert sorted(float(x['amount']) for x in costs['data']) == [23.5, 50.0]
assert len({x['repair_id'] for x in costs['data']})==1 and all(x['repair_id'] is not None for x in costs['data'])
invalid=call(f'/equipment/orders/{order}/accept','POST',{},token)
assert invalid.get('code') != 200, 'invalid transition accepted'
print('costs and invalid transition verified')
check('trial pass',call(f'/equipment/orders/{order}/trial','POST',{'result':'PASS','notes':'verified'},token))
check('close',call(f'/equipment/orders/{order}/close','POST',{},token))


history=call(f'/equipment/assets/{equipment}/history',token=token);check('equipment history',history)
assert any(x['id']==order and float(x['total_cost'])==73.5 for x in history['data']['orders'])
assert any(x['result']=='ABNORMAL' for x in history['data']['inspections'])
print('history verified')
detail=call(f'/equipment/orders/{order}',token=token);check('order detail',detail)
assert [(x['from_status'],x['to_status']) for x in detail['data']['transitions']] == [('NEW','REPORTED'),('REPORTED','ACCEPTED'),('ACCEPTED','ARRIVED'),('ARRIVED','TESTING'),('TESTING','COMPLETED'),('COMPLETED','CLOSED')]
print('state transition audit verified')
assert detail['data']['repair_date']==datetime.date.today().isoformat()
assert next(x for x in history['data']['orders'] if x['id']==order)['repair_date']==datetime.date.today().isoformat()
assert next(x for x in call('/equipment/orders',token=token)['data'] if x['id']==order)['repair_date']==datetime.date.today().isoformat()
print('repair date format verified across list, detail and history')


