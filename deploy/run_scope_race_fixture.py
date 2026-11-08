import base64,json,os,subprocess,time,urllib.request
from pathlib import Path
root=Path('/tmp/scope-race-20261105')
(root/'private'/'00000000-0000-4000-8000-000000000001.png').write_bytes(base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/6x0AAAAASUVORK5CYII='))
opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
token=None
for _ in range(60):
 try:
  req=urllib.request.Request('http://127.0.0.1:22090/prod-api/login',json.dumps({'username':'race_reader','password':'admin123'}).encode(),{'Content-Type':'application/json'})
  with opener.open(req,timeout=5) as response: result=json.load(response)
  token=result.get('token')
  if token: break
 except Exception: pass
 time.sleep(2)
if not token: raise SystemExit('isolated test login unavailable')
env=os.environ.copy()
for k in ['HTTP_PROXY','HTTPS_PROXY','ALL_PROXY','http_proxy','https_proxy','all_proxy','BASE_URL','EMS_BASE_URL']: env.pop(k,None)
env.update(PYTHONPATH='/tmp/scope-race-20261105/python',EMS_ISOLATED_FIXTURE='YES',EMS_TEST_HTTP_PORT='22090',EMS_TEST_MYSQL_PORT='23306',EMS_TEST_MYSQL_DATABASE='scope_test_race',EMS_TEST_MYSQL_USER='scope_race',EMS_TEST_MYSQL_PASSWORD='isolated-race-only-43',EMS_TEST_EQUIPMENT_ID='99001',EMS_TEST_ORDER_ID='99001',EMS_TEST_PHOTO_ID='99001',EMS_TEST_OLD_DEPT='99001',EMS_TEST_NEW_DEPT='99002',EMS_TEST_READER_TOKEN=token)
subprocess.run(['python3','deploy/order_scope_race_test.py'],env=env,check=True)
