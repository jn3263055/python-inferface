#!/usr/bin/env python
# -*- coding: utf-8 -*-
import sys
import time, urllib, urllib2, logging

__version__ = 'Beta 1'
#关于Python SDK，有任何问题，可联系xuhao05@baidu.com
__author__ = 'RMS(xuhao05)'

#开放平台接口采用的协议
__scheme__ = 'http'

#可选 ：dev 开发环境 online 线上环境
__env__ = 'online'

#True 或False ，将会跟踪并打印每一个http请求
__is_debug__ = True
#重定向debug的输出，默认值为打印到sys.stdout 标准输出
__debug_out__ = sys.stdout
#True 或 False 如果为True，将会把http响应的body 打印
__is_debug_response__ = True
#debug时， http请求参数的分隔线
__debug_process_delimiter__ = '........'
#debug时，多个http请求间的分隔线
__debug_delimiter__ = '#####'
# debug时，出现exception 时，输出的分隔线
__debug_warn_delimiter__ = '!!!!!!!!!'

if __env__ == 'dev':
    __host__ = 'yf-atm-ur-dev03.vm.baidu.com'
else:
    __host__ = 'api.rms.baidu.com'

'''
Python client SDK for RMS openplatform.
'''

try:
    import json
except ImportError:
    import simplejson as json
try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO


class APIError(StandardError):
    '''
    请求错误时，会抛出异常
    '''
    def __init__(self, error_code, error, request):
        self.error_code = error_code
        self.error = error
        self.request = request
        if __is_debug__:
            __debug_out__.write('%sAn ERROR has raised:error_code=>%s,error=>%s\n' % (__debug_warn_delimiter__, self.error_code, self.error))
        StandardError.__init__(self, error)

    def __str__(self):
        return 'APIError: %s: %s, request: %s' % (self.error_code, self.error, self.request)


def _parse_json(s):
    ' 将字符串解析成JsonDict '
    def _obj_hook(pairs):
        ' convert json object to python object '
        o = JsonDict()
        for k, v in pairs.iteritems():
            o[str(k)] = v
        return o
    return json.loads(s, object_hook=_obj_hook)


class JsonDict(dict):
    '继承自Dict，增加了"."操作符的访问'
    def __getattr__(self, attr):
        return self[attr]

    def __setattr__(self, attr, value):
        self[attr] = value

    def __getstate__(self):
        return self.copy()

    def __setstate__(self, state):
        self.update(state)


_HTTP_GET = 0
_HTTP_POST = 1

_METHOD_MAP = {_HTTP_GET: 'GET',  _HTTP_POST: 'POST'}


def _read_body(obj):
    '从http 响应中读取body'
    body = obj.read()
    return body


def _encode_params(**kw):
    '对http请求进行编码'
    args = []
    for k, v in kw.iteritems():
        qv = v.encode('utf-8') if isinstance(v, unicode) else str(v)
        args.append('%s=%s' % (k, urllib.quote(qv)))
    return '&'.join(args)


def _http_call(the_url, method, access_token, **kw):
    '''执行一个http 请求
    @param the_url string 要请求的url
    @param method enum _HTTP_GET _HTTP_POST
    @param access_token 可选，如果为空，不将token作为header头发送
    @param **kw 多余的key value作为url请求参数
    @return 返回请求body值解析过的，JsonDict 对象
    '''
    if __is_debug__:
        __debug_out__.write('%s Debug info :a %s http request start..%s\n' % (__debug_delimiter__, _METHOD_MAP[method], __debug_delimiter__))

    #send an http request and expect to return a json object if no error.
    params = None
    params = _encode_params(**kw)
    http_url = '%s?%s' % (the_url, params) if method == _HTTP_GET else the_url
    log = logging.getLogger('django')
    log.info(http_url)
    http_body = None if method == _HTTP_GET else params
    req = urllib2.Request(http_url, data=http_body)

    #debug output
    if __is_debug__:
        __debug_out__.write('%s URL:%s\n' % (__debug_process_delimiter__, http_url))
        if http_body is not None:
            __debug_out__.write('%s POST FIELD:%s\n' % (__debug_process_delimiter__, http_body))

    if access_token:
        req.add_header('ROP-Authorization', 'RopAuth %s' % access_token)
        #debug output
        if __is_debug__:
            __debug_out__.write('%s Header:ROP-Authorization:RopAuth %s\n' % (__debug_process_delimiter__, access_token))

    try:
        resp = urllib2.urlopen(req)
        body = _read_body(resp)
        if __is_debug__ and __is_debug_response__:
            __debug_out__.write('%s Response Body:%s\n' % (__debug_process_delimiter__, body))
        r = _parse_json(body)
        if hasattr(r, 'error_code'):
            raise APIError(r.error_code, r.get('msg', ''), vars(req))
        return r
    except urllib2.HTTPError, e:
        raise APIError(e.code, e.reason, vars(req))
    finally:
        if __is_debug__:
            __debug_out__.write('%s The url request trace ended%s\n' % (__debug_delimiter__, __debug_delimiter__))


class APIClient(object):
    '''
    ApiClient，当用户有一个Token时，用此对象执行接口访问
    '''
    def __init__(self, access_token, version='v1'):
        '''
        @param access_token string 某个app key 的access token
        @param version 可选 目前只运行v1
        '''
        self.access_token = access_token
        self.version = version
        self.api_url = '%s://%s/%s' % (__scheme__, __host__, self.version)
        self.expires = 0.0

    def set_access_token(self, access_token, expires):
        self.access_token = str(access_token)
        self.expires = float(expires)

    def is_expires(self):
        return not self.access_token or time.time() > self.expires

    def __getattr__(self, attr):
        if '__' in attr:
            return getattr(self.get, attr)

        return _Callable(self, attr)


class APIAuth(object):
    '''
    获取access token
    '''
    def __init__(self, app_key, secret_token):
        '''
        @param app_key app ID 可通过 http://open.rms.baidu.com/app 中应用的详细信息查看到
        @param secret_token Secret Token
        '''
        self.host = __host__
        self.app_key = app_key
        self.secret_token = secret_token
        self.scheme = __scheme__

    def get_access_token_url(self):
        return '%s://%s/%s' % (self.scheme, self.host, 'auth/accessToken')

    def special_access_token(self, user):
        return _http_call(self.get_access_token_url(), _HTTP_POST, '', app_key=self.app_key, secret_token=self.secret_token, generate_type='special_auth', user=user)

    def request_access_token(self, request_token):
        return _http_call(self.get_access_token_url(), _HTTP_POST, '', app_key=self.app_key, secret_token=self.secret_token, generate_type='request_token')


class _Executable(object):
    '''_Callable() 实例的 post 和 get 属性会返回一个_Executable 实例'''
    def __init__(self, client, method, path):
        self._client = client
        self._method = method
        self._path = path

    def __call__(self, **kw):
        return _http_call('%s/%s' % (self._client.api_url, self._path), self._method, self._client.access_token, **kw)

    def __str__(self):
        return '_Executable (%s %s)' % (self._method, self._path)

    __repr__ = __str__


class _Callable(object):
    '''ApiClient()实例的属性值，会返回一个_Callable()实例'''
    def __init__(self, client, name):
        self._client = client
        self._name = name

    def __getattr__(self, attr):
        if attr == 'get':
            return _Executable(self._client, _HTTP_GET, self._name)
        if attr == 'post':
            return _Executable(self._client, _HTTP_POST, self._name)
        name = '%s/%s' % (self._name, attr)
        return _Callable(self._client, name)

    def __str__(self):
        return '_Callable (%s)' % self._name

    __repr__ = __str__
