# -*- coding: utf-8 -*-
"""ima COS 上传脚本（第 15 轮）：按 cred_v15.json 凭证上传原型 HTML"""
import json, sys, io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

CRED = r"D:\self\sy\一体化管理\outputs\UI原型\_ima\cred_v15.json"
FILE = r"D:\self\sy\一体化管理\outputs\UI原型\IMS-一体化管理系统-UI原型.html"

with open(CRED, 'r', encoding='utf-8') as f:
    cred = json.load(f)

from qcloud_cos import CosConfig, CosS3Client

config = CosConfig(
    Region=cred['region'],
    SecretId=cred['secret_id'],
    SecretKey=cred['secret_key'],
    Token=cred['token'],
    Scheme='https'
)
client = CosS3Client(config)

with open(FILE, 'rb') as f:
    data = f.read()

client.put_object(
    Bucket=cred['bucket_name'],
    Key=cred['cos_key'],
    Body=data,
    ContentType='text/html'
)
print("UPLOAD_OK bytes=" + str(len(data)))
