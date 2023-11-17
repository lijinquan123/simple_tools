# -*- coding: utf-8 -*-
# @Author      : LJQ
# @Time        : 2023/3/10 17:01
# @Version     : Python 3.6.4
import json
import os
from contextlib import suppress

from simple_tools.patterns import FlyWeight


def path() -> str:
    return os.popen('whereis redis').read().strip()[6:]


def is_started() -> bool:
    return bool(int(os.popen("ps -ef|grep redis|grep -v grep|wc -l").read().strip()))


try:
    import redis
except ImportError:
    pass
else:
    class CustomRedis(redis.Redis):
        def get(self, name):
            value = super().get(name)
            if value == 'None' or not value:
                value = None
            if value and isinstance(value, (str, bytes, bytearray)):
                with suppress(Exception):
                    value = json.loads(value)
            return value

        def set(self, name, value, ex=None, px=None, nx=False, xx=False):
            value = value or ''
            if value and not isinstance(value, (str, bytes, bytearray)):
                value = json.dumps(value, ensure_ascii=False, separators=(',', ':'))
            return super().set(name, value, ex, px, nx, xx)


    class _RedisClient(metaclass=FlyWeight):
        def __init__(self, host, port, db, password: str = None):
            self.redis = CustomRedis(
                connection_pool=redis.ConnectionPool(host=host, port=port, db=db, password=password,
                                                     decode_responses=True)
            )


    def client(host: str, db: int, password: str = None) -> redis.Redis:
        return _RedisClient(host, 6379, db, password).redis
