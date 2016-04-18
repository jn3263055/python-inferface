#!/usr/bin/env python
# -*- coding: utf-8 -*-
import sys
import urllib2
import json
from rms import APIClient, APIAuth, APIError

APP_KEY = '109'
SECRET_TOKEN = 'b3c4614ad4194a10bb9762575acb43515a4cbafa'
MACHINEFILE = 'machine.list'


def _getIdByHostname(hostname):
    url = "http://rms.baidu.com/?r=interface/rest&handler=searchServers&show_fields=id&return_type=json&hostname=" + hostname
    req = urllib2.Request(url)
    res = json.loads(urllib2.urlopen(req).read())
    print(hostname + res[0]['id'])
    return res[0]['id']


if __name__ == '__main__':
    try:
        _dict = {}
        for line in open(MACHINEFILE):
            line = line.rstrip()
            machine_id = _getIdByHostname(line)
            _params = {}
            _params["HT"] = "ON"
            _dict[machine_id] = _params
        servers = json.dumps(_dict)
        print servers
        sys.exit()
        api_auth = APIAuth(APP_KEY, SECRET_TOKEN)
        result = api_auth.special_access_token('yaofaliang')
        token = result.access_token
        client = APIClient(access_token=token)
        result = client.unified_list.biosChange.get(servers=servers, skip_audit=0, auto_confirm=0)
        print result
    except APIError, e:
        print('Error in Calling RMS API')
