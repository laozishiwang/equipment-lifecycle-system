import json,urllib.request,urllib.error,uuid
base='http://127.0.0.1:18090/prod-api'
def call(path,token=None,data=None):
 h={'Content-Type':'application/json'}
 if token:h['Authorization']='Bearer '+token
 req=urllib.request.Request(base+path,None if data is None else json.dumps(data).encode(),h,method='GET' if data is None else 'POST')
 try:
  with urllib.request.urlopen(req,timeout=20) as r:return json.load(r)
 except urllib.error.HTTPError as e:return {'code':e.code}
def login(name):return call('/login',data={'username':name,'password':'admin123'})['token']
w=login('role_worker_test');other=login('smoke_worker');admin=login('admin');marker='ITEM-'+uuid.uuid4().hex[:8]
item={'name':marker,'result':'ABNORMAL','remark':'漏油'}
assert call('/equipment/inspections',w,{'equipmentId':1,'result':'NORMAL','items':[item]})['code']!=200
assert call('/equipment/inspections',w,{'equipmentId':1,'result':'ABNORMAL','items':[{'name':'','result':'NORMAL'}]})['code']!=200
assert call('/equipment/inspections',w,{'equipmentId':1,'result':'NORMAL','items':[{'name':'x','result':'NORMAL'}]*21})['code']!=200
r=call('/equipment/inspections',w,{'equipmentId':1,'result':'ABNORMAL','remark':'巡检异常','createOrder':True,'items':[item,{'name':'温度','result':'NORMAL','remark':''}]});assert r['code']==200
id=r['data']['inspectionId'];assert r['data']['orderId']
rows=call('/equipment/inspections/'+str(id)+'/items',w)['data'];assert len(rows)==2 and rows[0]['item_name']==marker and rows[0]['result']=='ABNORMAL'
assert call('/equipment/inspections/'+str(id)+'/items',other)['code']!=200
assert len(call('/equipment/inspections/'+str(id)+'/items',admin)['data'])==2
legacy=call('/equipment/inspections',w,{'equipmentId':1,'result':'NORMAL'});assert legacy['code']==200
assert call('/equipment/inspections/'+str(legacy['data']['inspectionId'])+'/items',w)['data']==[]
print('inspection item validation, atomic creation, role scope and legacy compatibility passed')
