import datetime,json,urllib.request,uuid
base='http://127.0.0.1:18090/prod-api'
def call(path,method='GET',data=None,token=None):
 h={'Content-Type':'application/json'}
 if token:h['Authorization']='Bearer '+token
 with urllib.request.urlopen(urllib.request.Request(base+path,None if data is None else json.dumps(data).encode(),h,method=method),timeout=15) as r:return json.load(r)
def all_plans(token):
 rows=[];query=''
 while True:
  page=call('/equipment/maintenance'+query,token=token)['data'];rows.extend(page)
  if len(page)<200:return rows
  last=page[-1];query='?afterActive=%s&afterDue=%s&afterId=%s'%(last['active'],last['next_due'],last['id'])
t=call('/login','POST',{'username':'admin','password':'admin123'})['token'];code='RET-'+uuid.uuid4().hex[:10]
assert call('/equipment/assets','POST',{'code':code,'name':'retire test'},t)['code']==200
eid=next(x['id'] for x in call('/equipment/assets?keyword='+code,token=t)['data'] if x['code']==code)
assert call('/equipment/maintenance','POST',{'equipmentId':eid,'title':code,'intervalDays':30,'nextDue':datetime.date.today().isoformat()},t)['code']==200
pid=next(x['id'] for x in all_plans(t) if x['title']==code)
payload={'name':'retire test','status':'RETIRED'}
assert call(f'/equipment/assets/{eid}','PUT',payload,t)['code']!=200
assert call(f'/equipment/maintenance/{pid}/deactivate','POST',{},t)['code']==200
assert call(f'/equipment/assets/{eid}','PUT',payload,t)['code']==200
print('active plan blocks retirement; deactivated plan permits retirement')

