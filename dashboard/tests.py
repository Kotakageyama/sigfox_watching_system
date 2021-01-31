from django.test import TestCase

from django.http.response import JsonResponse
import json
import requests

url = "http:///receive_json/"
sess = requests.session()

print(sess.get(url))

csrftoken = sess.cookies['csrftoken']

# ヘッダ
headers = {'Content-type': 'application/json',  "X-CSRFToken": csrftoken}

# 送信データ
prm = {"device": "test", "data": "082409240924092409240924"}

# JSON変換
params = json.dumps(prm)

# POST送信
res = sess.post(url, data=params, headers=headers)

# 戻り値を表示
print(json.loads(res.text))

