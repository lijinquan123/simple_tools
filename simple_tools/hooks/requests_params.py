# -*- coding: utf-8 -*-
# @Author      : LJQ
# @Time        : 2026/3/10 16:03
# @Version     : Python 3.14
from requests.sessions import Session

_original_send = Session.send


# PYTHONPATH=/home/test/hooks /usr/local/miniconda3/envs/python314/bin/vodd ...
def hooked_send(self, request, **kwargs):
    print(f"Hooked URL: {request.url}")
    print(f"Hooked Headers: {request.headers}")
    print(f"Hooked kwargs: {request.method} {kwargs}")
    response = _original_send(self, request, **kwargs)
    print(f"Hooked Status: {response.status_code} {response.url}")

    return response


Session.send = hooked_send
