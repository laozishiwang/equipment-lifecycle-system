import json, subprocess, urllib.parse, urllib.request, uuid
base='http://127.0.0.1:18090/prod-api'
tag='FILTER-'+uuid.uuid4().hex[:10]
def call(path, token=None, data=None):
    headers={'Content-Type':'application/json'}
    if token: headers['Authorization']='Bearer '+token
    req=urllib.request.Request(base+path, None if data is None else json.dumps(data).encode(), headers, method='GET' if data is None else 'POST')
    with urllib.request.urlopen(req,timeout=20) as response: return json.load(response)
def login(name): return call('/login',data={'username':name,'password':'admin123'})['token']
sql="INSERT INTO ems_work_order(equipment_id,reporter_id,description,status) VALUES "+','.join("(1,%d,'%s-%s','%s')"%(user,tag,label,status) for user,label,status in [(9010,'own-open','REPORTED'),(9010,'own-closed','CLOSED'),(1,'other-open','REPORTED')])+';'
p=subprocess.run(['docker','exec','-i','equipment-rebuild-mysql-1','sh','-c','mysql -uroot -p"$MYSQL_ROOT_PASSWORD" equipment_dev 2>/dev/null'],input=sql.encode(),capture_output=True);assert p.returncode==0
w=login('role_worker_test');t=login('role_tech_test');d=login('role_director_test')
for status in ['REPORTED','CLOSED']:
    rows=call('/equipment/orders?status='+status,w)['data']; assert rows and all(x['status']==status for x in rows)
    assert not any(x['description']==tag+'-other-open' for x in rows)
    assert any(x['description']==tag+('-own-open' if status=='REPORTED' else '-own-closed') for x in rows)
reported=call('/equipment/orders?status=REPORTED',t)['data'];assert any(x['description']==tag+'-other-open' for x in reported)
allrows=call('/equipment/orders?status=REPORTED',d)['data'];cursor=allrows[0]['id'];following=call('/equipment/orders?status=REPORTED&beforeId='+str(cursor),d)['data'];assert all(x['status']=='REPORTED' and x['id']<cursor for x in following)
assert call('/equipment/orders?status=INVALID',w)['code']!=200
def query(**params):return '/equipment/orders?'+urllib.parse.urlencode(params)
own=call(query(keyword=tag),w)['data'];assert len(own)==2 and all(tag in x['description'] for x in own)
assert len(call(query(keyword=tag,status='REPORTED'),w)['data'])==1
assert len(call(query(keyword=tag,status='REPORTED'),t)['data'])==2
assert call(query(keyword=tag+'%'),w)['data']==[]
assert call(query(keyword='x'*101),w)['code']!=200
assert call(query(keyword=str(own[0]['id'])),w)['data'][0]['id']==own[0]['id']
assert all(x['code']=='TEST-001' for x in call(query(keyword='TEST-001'),w)['data'])
bulk=tag+'-page'
sql="INSERT INTO ems_work_order(equipment_id,reporter_id,description,status) VALUES "+','.join("(1,9010,'%s-%03d','REPORTED')"%(bulk,i) for i in range(205))+';'
p=subprocess.run(['docker','exec','-i','equipment-rebuild-mysql-1','sh','-c','mysql -uroot -p"$MYSQL_ROOT_PASSWORD" equipment_dev 2>/dev/null'],input=sql.encode(),capture_output=True);assert p.returncode==0
first=call(query(keyword=bulk,status='REPORTED'),w)['data'];assert len(first)==200
second=call(query(keyword=bulk,status='REPORTED',beforeId=first[-1]['id']),w)['data'];assert len(second)==5
assert len({x['id'] for x in first+second})==205
print('order status filtering, cursor, invalid input and role scope passed')
