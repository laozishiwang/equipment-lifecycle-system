import datetime,json,urllib.request,urllib.error,uuid
base='http://127.0.0.1:18090/prod-api'
def call(path,method='GET',data=None,token=None):
 h={'Content-Type':'application/json'}
 if token:h['Authorization']='Bearer '+token
 req=urllib.request.Request(base+path,None if data is None else json.dumps(data).encode(),h,method=method)
 try:
  with urllib.request.urlopen(req,timeout=15) as r:return json.load(r)
 except urllib.error.HTTPError as e:return {'code':e.code}
def login(user):return call('/login','POST',{'username':user,'password':'admin123'})['token']
a=login('admin');w=login('smoke_worker');assert call('/equipment/maintenance/due-summary',token=w)['code'] in (401,403)
before=call('/equipment/maintenance/due-summary',token=a)['data'];code='ALERT-'+uuid.uuid4().hex[:10]
assert call('/equipment/assets','POST',{'code':code,'name':'alert test'},a)['code']==200
eid=next(x['id'] for x in call('/equipment/assets?keyword='+code,token=a)['data'] if x['code']==code)
today=datetime.date.today();assert call('/equipment/maintenance','POST',{'equipmentId':eid,'title':'today','intervalDays':30,'nextDue':today.isoformat()},a)['code']==200
assert call('/equipment/maintenance','POST',{'equipmentId':eid,'title':'overdue','intervalDays':30,'nextDue':(today-datetime.timedelta(days=1)).isoformat()},a)['code']==200
after=call('/equipment/maintenance/due-summary',token=a)['data'];assert int(after['due_today'])==int(before['due_today'])+1 and int(after['overdue'])==int(before['overdue'])+1
print('due summary counts and permission verified')
