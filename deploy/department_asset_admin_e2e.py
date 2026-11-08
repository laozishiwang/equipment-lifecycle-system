#!/usr/bin/env python3
"""Isolated-only asset admin scope acceptance. Creates one synthetic asset.
Requires EMS_ISOLATED_FIXTURE=YES, EMS_TEST_ADMIN_USER/PASSWORD,
EMS_TEST_A_USER/PASSWORD, EMS_TEST_A_DEPT_ID and EMS_TEST_DEVICE_1.
The limited account must have asset:add and access to EMS_TEST_A_DEPT_ID,
but no asset:history permission.
The target is fixed and proxies are ignored; never forward the port to production.
"""
import json, os, urllib.request, urllib.error, uuid
if os.getenv("EMS_ISOLATED_FIXTURE") != "YES": raise SystemExit("Refusing non-isolated run")
if any(k in os.environ for k in ("EMS_BASE_URL","BASE_URL","HTTP_PROXY","HTTPS_PROXY","ALL_PROXY")): raise SystemExit("Refusing proxy or custom target")
def req(name):
    value=os.getenv(name)
    if not value: raise SystemExit("Missing " + name)
    return value
opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
def call(path, data=None, token=None):
    headers={"Content-Type":"application/json"}
    if token: headers["Authorization"]="Bearer "+token
    request=urllib.request.Request("http://127.0.0.1:22090/prod-api"+path, data=None if data is None else json.dumps(data).encode(),headers=headers)
    try:
        with opener.open(request,timeout=20) as response: return json.load(response)
    except urllib.error.HTTPError as e: return {"code":e.code}
def login(prefix):
    r=call("/login",{"username":req(prefix+"_USER"),"password":req(prefix+"_PASSWORD")})
    if "token" not in r: raise AssertionError("login failed for "+prefix)
    return r["token"]
admin=login("EMS_TEST_ADMIN"); limited=login("EMS_TEST_A")
device=int(req("EMS_TEST_DEVICE_1"))
if device<=0: raise SystemExit("Invalid fixture ID")
dept=int(req("EMS_TEST_A_DEPT_ID"))
if dept<=0: raise SystemExit("Invalid department ID")
for label,token,body,history_allowed in (
    ("admin",admin,{},True),
    ("limited",limited,{"deptId":dept},False),
):
    create=call("/equipment/assets",{"code":"SCOPE-NEW-"+uuid.uuid4().hex[:10],"name":"isolated scope test",**body},token)
    history=call("/equipment/assets/%d/history"%device,token=token)
    if create.get("code")!=200 or (history.get("code")==200)!=history_allowed:
        raise AssertionError("unexpected result for "+label)
print("isolated admin asset creation and history permission passed")
