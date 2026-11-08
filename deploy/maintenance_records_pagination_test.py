import datetime,json,subprocess,urllib.error,urllib.request,uuid

base='http://127.0.0.1:18090/prod-api'
def call(path,token=None,data=None):
    headers={'Content-Type':'application/json'}
    if token: headers['Authorization']='Bearer '+token
    req=urllib.request.Request(base+path,None if data is None else json.dumps(data).encode(),headers,method='GET' if data is None else 'POST')
    try:
        with urllib.request.urlopen(req,timeout=30) as response: return json.load(response)
    except urllib.error.HTTPError as error: return {'code':error.code}
def login(name): return call('/login',data={'username':name,'password':'admin123'})['token']
admin,tech,worker=(login(x) for x in ('admin','role_tech_test','role_worker_test'))
title='RECORD-PAGE-'+uuid.uuid4().hex[:10]
created=call('/equipment/maintenance',admin,{'equipmentId':1,'title':title,'intervalDays':30,'nextDue':'2000-01-01'})
assert created['code']==200,created
plans=call('/equipment/maintenance',admin)['data']
plan=next(row['id'] for row in plans if row['title']==title)
values=','.join(f"({plan},1,'2026-01-01','page fixture {i}')" for i in range(205))
sql='INSERT INTO ems_maintenance_record(plan_id,completed_by,completed_date,notes) VALUES '+values+';'
run=subprocess.run(['docker','exec','-i','equipment-rebuild-mysql-1','sh','-c','exec mysql -uroot -p"$MYSQL_ROOT_PASSWORD" equipment_dev'],input=sql,text=True,capture_output=True,timeout=30)
assert run.returncode==0,run.stderr
first=call(f'/equipment/maintenance/{plan}/records',tech)
assert first['code']==200 and len(first['data'])==200,first
cursor=first['data'][-1]['id']
second=call(f'/equipment/maintenance/{plan}/records?beforeId={cursor}',tech)
assert second['code']==200 and len(second['data'])==5,second
ids=[row['id'] for row in first['data']+second['data']]
assert ids==sorted(set(ids),reverse=True) and len(ids)==205
assert call(f'/equipment/maintenance/{plan}/records?beforeId=0',tech)['code']!=200
assert call(f'/equipment/maintenance/{plan}/records',worker)['code']!=200
assert call(f'/equipment/maintenance/{plan}/records?beforeId={second["data"][-1]["id"]}',tech)['data']==[]
print('maintenance record pagination, uniqueness and permissions passed; fixture plan',plan)
