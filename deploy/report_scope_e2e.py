import os,json,urllib.request,urllib.parse,subprocess,io,zipfile,decimal
if os.getenv("EMS_ISOLATED_FIXTURE")!="YES":raise SystemExit("isolated fixture required")
base="http://127.0.0.1:22090/prod-api"
opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
def db(sql):subprocess.run(["docker","exec","-i","scope-race-20261105-mysql-1","sh","-c",'mysql -uroot -p"$MYSQL_ROOT_PASSWORD" scope_test_race 2>/dev/null'],input=sql.encode(),check=True)
def request(path,token=None,body=None):
 req=urllib.request.Request(base+path,None if body is None else json.dumps(body).encode(),{"Content-Type":"application/json",**({"Authorization":"Bearer "+token} if token else {})})
 with opener.open(req,timeout=30) as r:
  b=r.read();return json.loads(b) if r.headers.get_content_type()=="application/json" else b
def login(name):return request("/login",body={"username":name,"password":"admin123"})["token"]
sql="""
UPDATE sys_role SET status='0',data_scope='3' WHERE role_id=99001;
INSERT IGNORE INTO sys_role_menu SELECT 99001,menu_id FROM sys_menu WHERE perms IN ('equipment:order:list','equipment:order:viewAll');
INSERT IGNORE INTO sys_user(user_id,dept_id,user_name,nick_name,password,status,del_flag) SELECT 99102,99002,'report_scope_b','Report B',password,'0','0' FROM sys_user WHERE user_id=1;
INSERT IGNORE INTO sys_user_role VALUES(99102,99001);
INSERT IGNORE INTO ems_equipment(id,code,name) VALUES(99101,'REPORT-A-99101','Report A'),(99102,'REPORT-B-99102','Report B');
INSERT INTO ems_equipment_department VALUES(99101,99001),(99102,99002) ON DUPLICATE KEY UPDATE dept_id=VALUES(dept_id);
INSERT IGNORE INTO ems_work_order(id,equipment_id,reporter_id,technician_id,description,status) VALUES(99101,99101,1,1,'REPORT-A','CLOSED'),(99102,99102,99001,1,'REPORT-B','CLOSED');
INSERT IGNORE INTO ems_work_order_repair(id,work_order_id,technician_id,repair_date,description) VALUES(99101,99101,1,'2020-01-02','A'),(99102,99102,1,'2020-01-02','B');
INSERT IGNORE INTO ems_repair_cost(id,work_order_id,category,description,amount) VALUES(99101,99101,'LABOR','A',11),(99102,99102,'PARTS','B',22);
INSERT IGNORE INTO ems_repair_cost_link VALUES(99101,99101),(99102,99102);
INSERT IGNORE INTO ems_fault_code(id,code,category,part,symptom,created_by) VALUES(99101,'REPORT-A-FAULT','A-cat','A-part','A-symptom',1),(99102,'REPORT-B-FAULT','B-cat','B-part','B-symptom',1);
INSERT IGNORE INTO ems_repair_fault_code VALUES(99101,99101,'REPORT-A-FAULT','A-cat','A-part','A-symptom'),(99102,99102,'REPORT-B-FAULT','B-cat','B-part','B-symptom');
"""
db(sql);a=login("race_reader");b=login("report_scope_b"); period="?startDate=2020-01-02&endDate=2020-01-02"
def check(token,expected,missing,total):
 cost=request('/equipment/overview/costs'+period,token)['data']; assert decimal.Decimal(str(cost['total']))==decimal.Decimal(total),cost
 ids={r['id'] for r in request('/equipment/overview/costs/orders'+period,token)['data']};assert expected in ids and missing not in ids,ids
 faults={r['code'] for r in request('/equipment/overview/faults'+period,token)['data']}; expected_code='REPORT-A-FAULT' if expected==99101 else 'REPORT-B-FAULT'; missing_code='REPORT-B-FAULT' if expected==99101 else 'REPORT-A-FAULT';assert expected_code in faults and missing_code not in faults,faults
 q=urllib.parse.urlencode(dict(code=expected_code,category='A-cat' if expected==99101 else 'B-cat',part='A-part' if expected==99101 else 'B-part',symptom='A-symptom' if expected==99101 else 'B-symptom',startDate='2020-01-02',endDate='2020-01-02'))
 assert expected in {x['id'] for x in request('/equipment/overview/faults/orders?'+q,token)['data']}
 for route in ('costs','faults'):
  data=request('/equipment/overview/'+route+'/export'+period,token); z=zipfile.ZipFile(io.BytesIO(data)); raw=b''.join(z.read(x) for x in z.namelist() if x.startswith('xl/') and x.endswith('.xml')); assert (str(expected).encode() if route=='costs' else expected_code.encode()) in raw; assert (str(missing).encode() if route=='costs' else missing_code.encode()) not in raw
check(a,99101,99102,'11');check(b,99102,99101,'22')
assert request('/equipment/orders/99102',a)['code']==200,'participant cannot see order'
db('UPDATE ems_equipment_department SET dept_id=99002 WHERE equipment_id=99101')
assert decimal.Decimal(str(request('/equipment/overview/costs'+period,a)['data']['total']))==0
assert decimal.Decimal(str(request('/equipment/overview/costs'+period,b)['data']['total']))==33
assert {99101,99102}.issubset({r['id'] for r in request('/equipment/overview/costs/orders'+period,b)['data']})
assert not request('/equipment/overview/faults'+period,a)['data']
assert {'REPORT-A-FAULT','REPORT-B-FAULT'}.issubset({r['code'] for r in request('/equipment/overview/faults'+period,b)['data']})
for code,category,part,symptom,ident in [('REPORT-A-FAULT','A-cat','A-part','A-symptom',99101),('REPORT-B-FAULT','B-cat','B-part','B-symptom',99102)]:
 q=urllib.parse.urlencode(dict(code=code,category=category,part=part,symptom=symptom,startDate='2020-01-02',endDate='2020-01-02'))
 assert ident in {x['id'] for x in request('/equipment/overview/faults/orders?'+q,b)['data']}
 assert ident not in {x['id'] for x in request('/equipment/overview/faults/orders?'+q,a)['data']}
for route in ('costs','faults'):
 empty=request('/equipment/overview/'+route+'/export'+period,a);z=zipfile.ZipFile(io.BytesIO(empty));raw=b''.join(z.read(x) for x in z.namelist() if x.startswith('xl/') and x.endswith('.xml'))
 assert not any(value in raw for value in ((b'99101',b'99102') if route=='costs' else (b'REPORT-A-FAULT',b'REPORT-B-FAULT')))
 data=request('/equipment/overview/'+route+'/export'+period,b);z=zipfile.ZipFile(io.BytesIO(data));raw=b''.join(z.read(x) for x in z.namelist() if x.startswith('xl/') and x.endswith('.xml'))
 assert all(value in raw for value in ((b'99101',b'99102') if route=='costs' else (b'REPORT-A-FAULT',b'REPORT-B-FAULT')))
print('report A/B costs faults drilldown exports, participation exception, transfer passed')
