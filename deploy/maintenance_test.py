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
a=call('/login','POST',{'username':'admin','password':'admin123'})['token'];code='MAINT-'+uuid.uuid4().hex[:10]
assert call('/equipment/assets','POST',{'code':code,'name':'maintenance test'},a)['code']==200
eid=next(x['id'] for x in call('/equipment/assets?keyword='+code,token=a)['data'] if x['code']==code)
today=datetime.date.today();due=today.isoformat();title='test-'+uuid.uuid4().hex[:8]
assert call('/equipment/maintenance','POST',{'equipmentId':eid,'title':title,'intervalDays':30,'nextDue':due},a)['code']==200
plan=next(x for x in all_plans(a) if x['title']==title);pid=plan['id']; assert plan['due_status']=='DUE'
payload={'completedDate':due,'notes':'test service'}
assert call(f'/equipment/maintenance/{pid}/complete','POST',payload,a)['code']==200
assert call(f'/equipment/maintenance/{pid}/complete','POST',payload,a)['code']!=200
updated=next(x for x in all_plans(a) if x['id']==pid)
print('returned next_due:',repr(updated['next_due'])); assert str(updated['next_due'])[:10]==(today+datetime.timedelta(days=30)).isoformat(); assert updated['due_status']=='UPCOMING'
assert len(call(f'/equipment/maintenance/{pid}/records',token=a)['data'])==1
print('maintenance create, complete, next due and duplicate protection passed')

assert call(f'/equipment/maintenance/{pid}','PUT',{'title':'edited plan','intervalDays':60,'nextDue':due},a)['code']==200
assert call(f'/equipment/maintenance/{pid}/deactivate','POST',{},a)['code']==200
assert call(f'/equipment/maintenance/{pid}/complete','POST',payload,a)['code']!=200
records=call(f'/equipment/maintenance/{pid}/records',token=a)['data'];assert len(records)==1
inactive=next(x for x in all_plans(a) if x['id']==pid); assert inactive['due_status']=='INACTIVE'
print('edit, deactivate and retained records verified')

history=call(f'/equipment/assets/{eid}/history',token=a)['data']
assert any(x['title']=='edited plan' and x['notes']=='test service' and x['completed_date']==due for x in history['maintenance'])
print('equipment maintenance history verified')

