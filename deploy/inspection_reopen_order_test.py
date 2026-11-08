import concurrent.futures, datetime, json, threading, urllib.error, urllib.request, uuid

base='http://127.0.0.1:18090/prod-api'
def call(path, token=None, data=None):
    headers={'Content-Type':'application/json'}
    if token: headers['Authorization']='Bearer '+token
    req=urllib.request.Request(base+path,None if data is None else json.dumps(data).encode(),headers,method='GET' if data is None else 'POST')
    try:
        with urllib.request.urlopen(req,timeout=30) as response: return json.load(response)
    except urllib.error.HTTPError as error: return {'code':error.code}
def login(user): return call('/login',data={'username':user,'password':'admin123'})['token']
worker,admin,tech,other=(login(user) for user in ('role_worker_test','admin','role_tech_test','smoke_worker'))
created=call('/equipment/inspections',worker,{'equipmentId':1,'result':'ABNORMAL','remark':'reopen-'+uuid.uuid4().hex[:8],'createOrder':True})
assert created['code']==200,created
inspection,old=created['data']['inspectionId'],created['data']['orderId']
def reopen(): return call(f'/equipment/inspections/{inspection}/work-order',worker,{'description':'故障仍存在'})
assert reopen()['code']!=200
assert call(f'/equipment/orders/{old}/withdraw',worker,{'reason':'录入有误'})['code']==200
barrier=threading.Barrier(2)
def attempt(_): barrier.wait(); return reopen()
with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool: results=list(pool.map(attempt,range(2)))
assert sum(result.get('code')==200 for result in results)==1,results
new=next(result['data']['orderId'] for result in results if result.get('code')==200)
assert new!=old
row=next(x for x in call('/equipment/inspections',worker)['data'] if x['id']==inspection)
assert row['order_id']==new and row['order_status']=='REPORTED',row
oldDetail=call(f'/equipment/orders/{old}',worker)['data']
assert oldDetail['status']=='CANCELLED' and oldDetail['cancellation']['reason']=='录入有误'
assert reopen()['code']!=200
assert call(f'/equipment/orders/{new}/accept',tech,{})['code']==200
assert reopen()['code']!=200
assert call(f'/equipment/orders/{new}/cancel',admin,{'reason':'测试取消'})['code']==200
third=reopen()['data']['orderId']
assert call(f'/equipment/orders/{third}/accept',tech,{})['code']==200
assert call(f'/equipment/orders/{third}/arrive',tech,{})['code']==200
assert call(f'/equipment/orders/{third}/complete',tech,{'repairDate':datetime.date.today().isoformat(),'description':'完成修理','costs':[]})['code']==200
assert call(f'/equipment/orders/{third}/trial',tech,{'result':'PASS','notes':'正常'})['code']==200
assert call(f'/equipment/orders/{third}/close',admin,{})['code']==200
assert reopen()['code']!=200
history=call(f'/equipment/inspections/{inspection}/work-orders',worker)
assert history['code']==200 and [x['id'] for x in history['data']]==[third,new,old],history
assert [x['status'] for x in history['data']]==['CLOSED','CANCELLED','CANCELLED']
assert [x['id'] for x in call(f'/equipment/inspections/{inspection}/work-orders?beforeId={third}',worker)['data']]==[new,old]
assert call(f'/equipment/inspections/{inspection}/work-orders?beforeId=0',worker)['code']!=200
assert call(f'/equipment/inspections/{inspection}/work-orders',other)['code']!=200
assert len(call(f'/equipment/inspections/{inspection}/work-orders',admin)['data'])==3
separate=call('/equipment/inspections',worker,{'equipmentId':1,'result':'ABNORMAL','remark':'scope-test'})['data']['inspectionId']
def visible_row(): return next(x for x in call('/equipment/inspections',worker)['data'] if x['id']==separate)
assert visible_row()['can_report'] in (1,True)
adminOrder=call(f'/equipment/inspections/{separate}/work-order',admin,{'description':'管理员报修'})['data']['orderId']
row=visible_row()
assert row['order_id'] is None and row['order_status'] is None and row['can_report'] in (0,False),row
assert call(f'/equipment/inspections/{separate}/work-orders',worker)['data']==[]
assert call(f'/equipment/inspections/{separate}/work-orders',admin)['data'][0]['id']==adminOrder
assert call(f'/equipment/orders/{adminOrder}/cancel',admin,{'reason':'管理员取消'})['code']==200
assert visible_row()['can_report'] in (1,True)
assert call(f'/equipment/inspections/{separate}/work-order',worker,{'description':'仍有故障'})['code']==200
print('cancelled inspection work order re-report: history, concurrency and active-order guard passed')
