import json,subprocess,urllib.request,urllib.error,uuid
base='http://127.0.0.1:18090/prod-api';tag='PAGE-'+uuid.uuid4().hex[:10]
def call(path,token):
 req=urllib.request.Request(base+path,headers={'Authorization':'Bearer '+token})
 with urllib.request.urlopen(req,timeout=15) as r:return json.load(r)
def login():
 req=urllib.request.Request(base+'/login',json.dumps({'username':'smoke_worker','password':'admin123'}).encode(),{'Content-Type':'application/json'})
 with urllib.request.urlopen(req,timeout=15) as r:return json.load(r)['token']
orders=','.join("(1,9001,'%s-worker-%03d','CLOSED')"%(tag,i) for i in range(205))+","+','.join("(1,1,'%s-private-%03d','CLOSED')"%(tag,i) for i in range(5))
inspections=','.join("(1,9001,NOW(),'NORMAL','%s-worker-%03d')"%(tag,i) for i in range(205))+","+','.join("(1,1,NOW(),'NORMAL','%s-private-%03d')"%(tag,i) for i in range(5))
sql="INSERT INTO ems_work_order(equipment_id,reporter_id,description,status) VALUES "+orders+"; INSERT INTO ems_inspection(equipment_id,inspector_id,inspected_at,result,remark) VALUES "+inspections+";"
p=subprocess.run(['docker','exec','-i','equipment-rebuild-mysql-1','sh','-c','mysql -uroot -p"$MYSQL_ROOT_PASSWORD" equipment_dev 2>/dev/null'],input=sql.encode(),capture_output=True);assert p.returncode==0
worker=login()
for endpoint,field in [('/equipment/orders','description'),('/equipment/inspections','remark')]:
 first=call(endpoint,worker)['data'];assert len(first)==200
 second=call(endpoint+'?beforeId='+str(first[-1]['id']),worker)['data']
 ids=[x['id'] for x in first+second];assert len(ids)==len(set(ids))
 selected=[x for x in first+second if tag in x[field]]
 assert len(selected)==205 and all('private' not in x[field] for x in selected)
 assert all(x['id']<first[-1]['id'] for x in second)
 print(endpoint,'pagination and permission passed')
