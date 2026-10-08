# -*- coding: utf-8 -*-
"""ima COS 上传：AIR 模块 PRD V1（markdown）"""
import json, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

CRED = r"D:\self\sy\一体化管理\outputs\UI原型\_ima\cred_air.md.json"
FILE = r"D:\self\sy\一体化管理\outputs\产品PRD\IMS-模块20-AI资源中台PRD-V1.md"

with open(CRED, 'r', encoding='utf-8') as f:
    cred = json.load(f)

from qcloud_cos import CosConfig, CosS3Client
client = CosS3Client(CosConfig(
    Region=cred['region'], SecretId=cred['secret_id'],
    SecretKey=cred['secret_key'], Token=cred['token'], Scheme='https'))

with open(FILE, 'rb') as f:
    data = f.read()
client.put_object(Bucket=cred['bucket_name'], Key=cred['cos_key'], Body=data, ContentType='text/markdown')
print("UPLOAD_OK bytes=" + str(len(data)))
