import base64,concurrent.futures,json,os,subprocess,time,urllib.request,urllib.error,uuid,pymysql
if os.environ.get('EMS_ISOLATED_FIXTURE')!='YES':raise SystemExit('isolated fixture required')
base='http://127.0.0.1:22090/prod-api';opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
def sql(q):
 return subprocess.run(['docker','exec','-i','scope-race-20261105-mysql-1','sh','-c','mysql -uroot -p"$MYSQL_ROOT_PASSWORD" scope_test_race -N 2>/dev/null'],input=q.encode(),stdout=subprocess.PIPE,check=True).stdout.decode().strip()
def request(path,token=None,body=None,content='application/json'):
 r=urllib.request.Request(base+path,body,{'Content-Type':content,**({'Authorization':'Bearer '+token} if token else {})})
 try:
  with opener.open(r,timeout=25) as x:return json.load(x)
 except urllib.error.HTTPError as e:return {'code':e.code}
def upload(i,t):
 b='boundary'+uuid.uuid4().hex;png=base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/6x0AAAAASUVORK5CYII='); data=('--'+b+'\r\nContent-Disposition: form-data; name="file"; filename="fixture.png"\r\nContent-Type: image/png\r\n\r\n').encode()+png+('\r\n--'+b+'--\r\n').encode();return request('/equipment/orders/%d/photos'%i,t,data,'multipart/form-data; boundary='+b)
sql("INSERT IGNORE INTO sys_role_menu SELECT 99001,menu_id FROM sys_menu WHERE perms IN ('equipment:order:photo','equipment:order:viewAll')")
t=request('/login',body=json.dumps({'username':'race_reader','password':'admin123'}).encode())['token']
assert upload(99001,t)['code']==200, 'initial upload must succeed'
sql("DELETE rm FROM sys_role_menu rm JOIN sys_menu m ON m.menu_id=rm.menu_id WHERE rm.role_id=99001 AND m.perms='equipment:order:viewAll'")
assert upload(99001,t)['code']!=200, 'revoked viewAll must deny old token'
print('revoked viewAll denied')
