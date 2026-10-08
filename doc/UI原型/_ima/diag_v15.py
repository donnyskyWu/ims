# -*- coding: utf-8 -*-
"""诊断脚本：直接打印签名要素，用 requests + COS XML API 签名 PUT 上传"""
import json, sys, io, base64, hashlib, hmac, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

CRED = r"D:\self\sy\一体化管理\outputs\UI原型\_ima\cred_v15.json"
FILE = r"D:\self\sy\一体化管理\outputs\UI原型\IMS-一体化管理系统-UI原型.html"

with open(CRED, 'r', encoding='utf-8') as f:
    cred = json.load(f)

print("sid head:", cred['secret_id'][:20])
print("key len:", len(cred['secret_key']), "tail:", repr(cred['secret_key'][-4:]))
print("token head:", cred['token'][:20])
print("key:", cred['cos_key'])

# 尝试 base64 解码 secret_key（若是 base64 形式，COS SDK 直接使用原始字符串）
try:
    dk = base64.b64decode(cred['secret_key'])
    print("b64 decode ok, len:", len(dk))
except Exception as e:
    print("b64 decode fail:", e)

import requests

key = cred['secret_key']
sid = cred['secret_id']
token = cred['token']
host = cred['bucket_name'] + '.cos.' + cred['region'] + '.myqcloud.com'

# COS XML API 签名（q-sign-algorithm=sha1）
def q_sign(key, sid, exp, start, path, params=''):
    sk = base64.b64decode(key) if key.endswith('=') or key.endswith('==') else key.encode()
    # SecretKey 直接使用字符串
    sk = key.encode('utf-8')
    qk = 'q-sign-algorithm=sha1&q-ak=' + sid + '&q-sign-time=' + str(start) + ';' + str(exp)
    # HttpString: method\nuri\nparams\nheaders
    httpstr = 'put\n/' + path + '\n\n\n'
    sxi = hashlib.sha1(sk).hexdigest()
    sxf = hmac.new(sxi.encode(), httpstr.encode(), hashlib.sha1).hexdigest()
    sign = hmac.new(sxi.encode(), (qk + '&' + sxf).encode(), hashlib.sha1).hexdigest()
    return qk + '&q-key-time=' + str(start) + ';' + str(exp) + '&q-header-list=&q-url-param-list=&q-signature=' + sign

now = int(time.time())
exp = now + 3600
auth = q_sign(key, sid, exp, now, cred['cos_key'])
# 临时密钥需要 x-cos-security-token
headers = {
    'Authorization': auth,
    'x-cos-security-token': token,
    'Content-Type': 'text/html'
}
url = 'https://' + host + '/' + cred['cos_key']
with open(FILE, 'rb') as f:
    data = f.read()
r = requests.put(url, data=data, headers=headers)
print("HTTP", r.status_code)
print(r.text[:500] if r.status_code != 200 else 'PUT_OK bytes=' + str(len(data)))
