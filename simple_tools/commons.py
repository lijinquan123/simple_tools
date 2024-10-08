# -*- coding: utf-8 -*-
# @Author      : LJQ
# @Time        : 2023/3/10 16:40
# @Version     : Python 3.6.4
import datetime
import functools
import importlib
import inspect
import logging
import math
import multiprocessing
import os
import platform
import random
import socket
import sys
import threading
import time
from pathlib import Path
from urllib.parse import urlparse

from requests.cookies import RequestsCookieJar
from requests.utils import cookiejar_from_dict, dict_from_cookiejar

default_logger = logging.getLogger(__name__)


def codeblock_execute_limit(times: int = 1):
    """代码块执行次数限制,默认只执行1次"""
    if not hasattr(codeblock_execute_limit, 'codeblocks'):
        setattr(codeblock_execute_limit, 'codeblocks', {})

    f = sys._getframe(1)
    k = f'{f.f_code.co_filename}:{f.f_lineno}'
    codeblocks = getattr(codeblock_execute_limit, 'codeblocks')
    if (cur_times := codeblocks.get(k, 0)) >= times:
        return False
    codeblocks[k] = cur_times + 1
    return True


def locale_compare(strings: str):
    # 实现JavaScript中的localeCompare
    # 符号 < 0-9 < a < A < ... < z < Z
    oxs = []
    for x in strings:
        ox = ord(x)
        if 48 <= ox <= 57:
            ox = ox + 1000
        elif 97 <= ox <= 122:
            ox = ox + 2000 - 32.5
        elif 65 <= ox <= 90:
            ox = ox + 2000
        oxs.append(ox)
    return oxs


def is_windows() -> bool:
    return platform.system().lower() == 'windows'


IS_WINDOWS = is_windows()


def fix_filename(filename: str, pairs: list = None):
    if not pairs:
        pairs = [
            ('/', '／'),
            # 文件名允许有网址
            # ('.', '。'),
            ('\\', '＼'),
            ('?', '？'),
            ('*', '＊'),
            (':', '：'),
            ('"', '“'),
            ('<', '＜'),
            ('>', '＞'),
            ('|', '｜'),
        ]
    for pair in pairs:
        filename = filename.replace(*pair)
    return filename


def get_domain_ip(domain: str) -> str:
    return socket.gethostbyname(domain)


def _get_extranet_ip() -> str:
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]

    return ip


# 网络中断时,会产生OSError: [Errno 101] Network is unreachable异常,导致网络服务线程结束,进而重启失败,网络服务停止
EXTRANET_IP = _get_extranet_ip()


def is_subprocess() -> bool:
    """
    判断当前进程是否为子进程
    :return:
    """
    if sys.version_info >= (3, 8):
        return bool(multiprocessing.process.parent_process())
    else:
        cur_process = multiprocessing.current_process().name
        return cur_process != 'MainProcess'


def makekeys(args: tuple, kwargs: dict) -> tuple:
    """
    将关键字参数与排序与元组拼接
    Args:
        args: 位置参数
        kwargs: 关键字参数
    Returns: 拼接后的元组
    """
    for item in sorted(kwargs.items(), key=lambda x: x[0]):
        args += tuple(item)
    return args


def ciphers(length: int, base: str = '0123456789abcdef') -> str:
    seed = math.ceil(length / len(base)) * base
    return ''.join(random.sample(seed, length))


def build_key(provider: str = '', unique_id: str = '', suffix: str = ''):
    return '_'.join(filter(bool, [provider, unique_id, suffix]))


class CookieConverter(object):
    @staticmethod
    def get_cookie_str(cookies) -> str:
        if not cookies:
            return ''
        if isinstance(cookies, RequestsCookieJar):
            cookies = dict_from_cookiejar(cookies)
        cookie = '; '.join([f'{k}={v}' for k, v in cookies.items()])
        return cookie

    @staticmethod
    def get_cookie_dict(cookies) -> dict:
        if not cookies:
            return {}
        if isinstance(cookies, str):
            cookie_dict = {}
            for cookie_pair in cookies.split('; '):
                k, v = cookie_pair.split('=', 1)
                cookie_dict[k] = v
            return cookie_dict
        elif isinstance(cookies, RequestsCookieJar):
            return dict_from_cookiejar(cookies)
        elif isinstance(cookies, dict):
            return cookies

    @staticmethod
    def get_cookiejar(cookies) -> RequestsCookieJar:
        if isinstance(cookies, str):
            cookies = CookieConverter.get_cookie_dict(cookies)
        if isinstance(cookies, dict):
            cookies = cookiejar_from_dict(cookies)
        return cookies


class Clock(object):

    @staticmethod
    def date() -> str:
        return time.strftime('%Y-%m-%d %H:%M:%S')

    @staticmethod
    def timestamp() -> int:
        return int(time.time())

    @staticmethod
    def millisecond() -> int:
        return int(time.time() * 1000)

    @staticmethod
    def date_to_timestamp(date: str, fmt: str = '%Y-%m-%d %H:%M:%S') -> float:
        if not date:
            return 0
        if isinstance(date, float):
            return date
        return time.mktime(time.strptime(date, fmt))

    @staticmethod
    def timestamp_to_date(timestamp: int, fmt: str = '%Y-%m-%d %H:%M:%S') -> str:
        if not timestamp:
            return ''
        if isinstance(timestamp, str):
            return timestamp
        return time.strftime(fmt, time.localtime(timestamp))


class FunctionResult(object):
    _caches = {}

    @classmethod
    def cache(cls, duration: float):
        def _cache(func):
            @functools.wraps(func)
            def __cache(*args, **kwargs):
                if not hasattr(func, '__function_result_lock'):
                    func.__function_result_lock = threading.RLock()
                key = func, makekeys(args, kwargs)
                if key not in cls._caches or time.time() - cls._caches[key][1] > duration:
                    with func.__function_result_lock:
                        result = func(*args, **kwargs)
                        cls._caches[key] = result, time.time()
                return cls._caches[key][0]

            return __cache

        return _cache


def get_plugin_map(base_cls: type, filter_stems: tuple = None, module: str = None, **kwargs):
    logger = kwargs.get('logger') or default_logger
    cls_file = Path(inspect.getfile(base_cls))
    if module is None:
        module = base_cls.__module__
        if cls_file.stem != '__init__' and module[-len(cls_file.stem):] == cls_file.stem:
            module = module[:-len(cls_file.stem) - 1]
    if filter_stems is None:
        filter_stems = '__init__', cls_file.stem
    for file in cls_file.parent.iterdir():
        if file.is_file() and file.suffix == '.py' and file.stem not in filter_stems:
            try:
                importlib.import_module(f'{module}.{file.stem}')
            except Exception as e:
                logger.exception(e)
    plugin_map = {}

    def add_plugin(cls):
        usable = getattr(cls, 'usable', None)
        if not usable:
            return False
        provider = getattr(cls, 'provider', None)
        if not isinstance(provider, str):
            provider = cls.__module__.rsplit('.', 1)[-1]
        plugin_map[provider] = cls
        return True

    def fill_support_plugin(cls):
        if not add_plugin(cls):
            return
        for subclass in cls.__subclasses__():
            if not add_plugin(subclass):
                continue
            if subclass.__subclasses__():
                fill_support_plugin(subclass)

    fill_support_plugin(base_cls)
    return dict(sorted(plugin_map.items(), key=lambda x: x[0]))


def get_subclasses(base_cls: type):
    subclasses = {}

    def fill_subclasses(cls):
        for subclass in cls.__subclasses__():
            if subclass.__subclasses__():
                fill_subclasses(subclass)
            else:
                usable = getattr(subclass, 'usable', None)
                if not usable:
                    continue
                subclasses[subclass.__name__] = subclass

    fill_subclasses(base_cls)
    return dict(sorted(subclasses.items(), key=lambda x: x[0]))


class CPUTimer(object):
    """
    CPU计时器(上下文管理器)
    当前线程在某一时间段内的CPU利用率计算公式:
        CPU利用率 = CPU时间 / 运行时间 * 100%
    """

    def __init__(self, tag: str = '', **kwargs):
        if tag:
            tag = f'<{tag}> '
        self.tag = tag
        self.logger = kwargs.get('logger') or default_logger

    def __enter__(self):
        self.start = time.time()
        self.thread_clock_id = time.CLOCK_THREAD_CPUTIME_ID
        self.thread_cpu_start = time.clock_gettime(self.thread_clock_id)

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.thread_cpu_end = time.clock_gettime(self.thread_clock_id)
        self.end = time.time()
        thread_cpu_duration = self.thread_cpu_end - self.thread_cpu_start
        duration = self.end - self.start
        self.logger.warning(
            f'{self.tag}'
            f'CPU利用率: {round(100 * thread_cpu_duration / duration, 2)}%, '
            f'CPU时间: {round(thread_cpu_duration, 8)}, 运行时间: {round(duration, 8)}'
        )


class Timer(object):
    """
    计时器(上下文管理器)
    """

    def __init__(self, tag: str = '', **kwargs):
        if tag:
            tag = f'<{tag}> '
        self.tag = tag
        self.logger = kwargs.get('logger') or default_logger

    def __enter__(self):
        self.start = datetime.datetime.now().replace(microsecond=0)

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.end = datetime.datetime.now().replace(microsecond=0)
        self.logger.info(f'{self.tag}总共耗时: {self.end - self.start}')


class FrequencyLogger(logging.Logger):
    """
    频率日志

    控制当前行的日志输出频率
    """
    intervals = {}

    def _log(self, level, msg, args, exc_info=None, extra=None, stack_info=False, stacklevel=2, interval: int = 0):
        if interval > 0:
            try:
                fn, lno, func, sinfo = self.findCaller(stack_info, stacklevel)
            except ValueError:
                pass
            else:
                key = fn, lno
                last_time = self.intervals.get(key, 0)
                cur_time = time.time()
                if cur_time - last_time < interval:
                    return
                self.intervals[key] = cur_time

        super()._log(level, msg, args, exc_info, extra, stack_info, stacklevel)


class TestFrequencyLogger(FrequencyLogger):
    """
    频率日志测试版

    控制当前行的日志输出频率
    """

    def _log(self, level, msg, args, exc_info=None, extra=None, stack_info=False, stacklevel=2, interval: int = 0):
        super()._log(level, msg, args, exc_info, extra, stack_info, stacklevel, 0)


def read_backwards_nt(filepath: str, n: int = 1000, block_size: int = 1024, encoding='utf-8'):
    """从后向前读取文件行内容"""
    # 适用于文件行数超过`一百万`,读取不超过`一千`的情况
    with open(filepath, 'rb') as file:
        file.seek(0, 2)  # 移动到文件末尾
        end = file.tell()  # 获取文件大小（字节数）
        lines = []
        buffer = bytearray()

        while len(lines) <= n and end > 0:
            size = min(block_size, end)
            end -= size
            file.seek(end)
            buffer = file.read(size) + buffer
            lines = buffer.split(b'\n')

        # 处理结果
        last_lines = lines[-n:] if len(lines) > n else lines
    return [line.decode(encoding) for line in last_lines]


def read_backwards_posix(filepath: str, n: int = 1000) -> list:
    """从后向前读取文件行内容"""
    command = f'tail -n {n} "{filepath}"'
    result = os.popen(command).read()
    return result.splitlines()


read_backwards = read_backwards_posix if os.name == 'posix' else read_backwards_nt


def change_url_to_file(url: str) -> Path:
    return Path(urlparse(url).path)
