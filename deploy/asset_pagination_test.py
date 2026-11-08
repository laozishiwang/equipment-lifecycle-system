import json,subprocess,urllib.request,uuid
base='http://127.0.0.1:18090/prod-api';tag='PAGEASSET-'+uuid.uuid4().hex[:8]
def call(path,token):
 with urllib.request.urlopen(urllib.request.Request(base+path,headers={'Authorization':'Bearer '+token}),timeout=15) as r:return json.load(r)
req=urllib.request.Request(base+'/login',json.dumps({'username':'admin','password':'admin123'}).encode(),{'Content-Type':'application/json'})
with urllib.request.urlopen(req,timeout=15) as r:token=json.load(r)['token']
values=','.join("('%s-%03d','pagination test')"%(tag,i) for i in range(205))
sql='INSERT INTO ems_equipment(code,name) VALUES '+values+';'
p=subprocess.run(['docker','exec','-i','equipment-rebuild-mysql-1','sh','-c','mysql -uroot -p"$MYSQL_ROOT_PASSWORD" equipment_dev 2>/dev/null'],input=sql.encode(),capture_output=True);assert p.returncode==0
first=call('/equipment/assets?keyword='+tag,token)['data'];assert len(first)==200
second=call('/equipment/assets?keyword='+tag+'&beforeId='+str(first[-1]['id']),token)['data'];assert len(second)==5
assert len({x['id'] for x in first+second})==205
assert all(x['code'].startswith(tag) for x in first+second)
assert all(x['id']<first[-1]['id'] for x in second)
print('equipment search pagination and cursor verified')
