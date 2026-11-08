import datetime,json,urllib.error,urllib.parse,urllib.request,uuid,zoneinfo

base='http://127.0.0.1:18090/prod-api'
def call(path,token=None,data=None):
    headers={'Content-Type':'application/json'}
    if token:headers['Authorization']='Bearer '+token
    req=urllib.request.Request(base+path,None if data is None else json.dumps(data).encode(),headers,method='GET' if data is None else 'POST')
    try:
        with urllib.request.urlopen(req,timeout=30) as response:return json.load(response)
    except urllib.error.HTTPError as error:return {'code':error.code}
def login(user):return call('/login',data={'username':user,'password':'admin123'})['token']
admin,tech,worker=(login(x) for x in ('admin','role_tech_test','role_worker_test'))
today=datetime.datetime.now(zoneinfo.ZoneInfo('Asia/Shanghai')).date()
tag='MAINTFILTER-'+uuid.uuid4().hex[:8]
for suffix,date in [('overdue',today-datetime.timedelta(days=1)),('due',today),('upcoming',today+datetime.timedelta(days=1)),('inactive',today)]:
    assert call('/equipment/maintenance',admin,{'equipmentId':1,'title':tag+'-'+suffix,'intervalDays':30,'nextDue':date.isoformat()})['code']==200
def query(**params):return '/equipment/maintenance?'+urllib.parse.urlencode(params)
rows=call(query(keyword=tag),tech)['data'];assert len(rows)==4,rows
inactive=next(x['id'] for x in rows if x['title']==tag+'-inactive')
assert call(f'/equipment/maintenance/{inactive}/deactivate',admin,{})['code']==200
for status,suffix in [('OVERDUE','overdue'),('DUE','due'),('UPCOMING','upcoming'),('INACTIVE','inactive')]:
    rows=call(query(keyword=tag,dueStatus=status),tech)['data']
    assert len(rows)==1 and rows[0]['title']==tag+'-'+suffix and rows[0]['due_status']==status,(status,rows)
assert call(query(keyword=tag,dueStatus='bad'),tech)['code']!=200
assert call(query(keyword='x'*101),tech)['code']!=200
assert call(query(keyword=tag),worker)['code']!=200
assert call(query(keyword=tag+'%'),tech)['data']==[]
assert any(x['title']==tag+'-due' for x in call(query(keyword=tag+'-due'),tech)['data'])
assert all(x['code']=='TEST-001' for x in call(query(keyword='TEST-001'),tech)['data'])
print('maintenance keyword, status, literal wildcards and role permissions passed')
