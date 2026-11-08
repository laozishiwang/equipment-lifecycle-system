import json,subprocess,urllib.parse,urllib.request,uuid
base='http://127.0.0.1:18090/prod-api';tag='PLANPAGE-'+uuid.uuid4().hex[:8]
def call(path,token):
 with urllib.request.urlopen(urllib.request.Request(base+path,headers={'Authorization':'Bearer '+token}),timeout=15) as r:return json.load(r)
req=urllib.request.Request(base+'/login',json.dumps({'username':'admin','password':'admin123'}).encode(),{'Content-Type':'application/json'})
with urllib.request.urlopen(req,timeout=15) as r:token=json.load(r)['token']
values=','.join("(1,'%s-active-%03d',30,'2000-01-01',1,1)"%(tag,i) for i in range(205))+','+','.join("(1,'%s-inactive-%03d',30,'2000-01-01',0,1)"%(tag,i) for i in range(5))
sql='INSERT INTO ems_maintenance_plan(equipment_id,title,interval_days,next_due,active,created_by) VALUES '+values+';'
p=subprocess.run(['docker','exec','-i','equipment-rebuild-mysql-1','sh','-c','mysql -uroot -p"$MYSQL_ROOT_PASSWORD" equipment_dev 2>/dev/null'],input=sql.encode(),capture_output=True);assert p.returncode==0
allrows=[];params=''
while True:
 page=call('/equipment/maintenance'+params,token)['data'];allrows+=page
 if len(page)<200:break
 last=page[-1];params='?'+urllib.parse.urlencode({'afterActive':last['active'],'afterDue':last['next_due'],'afterId':last['id']})
assert len({x['id'] for x in allrows})==len(allrows)
assert sum(x['title'].startswith(tag) for x in allrows)==210
keys=[(-int(x['active']),x['next_due'],-int(x['id'])) for x in allrows];assert keys==sorted(keys)
query={'keyword':tag,'dueStatus':'OVERDUE'}
first=call('/equipment/maintenance?'+urllib.parse.urlencode(query),token)['data'];assert len(first)==200
last=first[-1];query.update({'afterActive':last['active'],'afterDue':last['next_due'],'afterId':last['id']})
second=call('/equipment/maintenance?'+urllib.parse.urlencode(query),token)['data'];assert len(second)==5
assert len({x['id'] for x in first+second})==205 and all(x['due_status']=='OVERDUE' for x in first+second)
print('maintenance pagination: same-date ties, active boundary and uniqueness passed')
