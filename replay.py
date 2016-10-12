#!/usr/bin/evn python
# -*- coding:utf-8 -*-
# @author: zhangzhao_lenovo@126.com
# @date: 20161005
# @version: 1.0.0.1009
import os
import sys
import requests
from collections import deque
import time
import urllib.parse
import middleware
import difflib
import pickle
import json
import datetime
import re

def readfile(fpath,encoding='utf-16-le'):
    with open(fpath, 'r',encoding) as f:
        while True:
            block = f.readline()
            if block:
                yield block
            else:
                return

def getlasttestcase(x):
    l = os.listdir(x)
    l.sort(key=lambda fn: os.path.getmtime(x+fn) if (not os.path.isdir(x+fn)
                                                     and (os.path.splitext(fn))[-1] == '.txt') else 0)
    return x+l[-1]

def getdate():
    return time.strftime("%Y-%m-%d-%H-%M-%S", time.localtime(time.time()))

def getwhitelist():
    if not os.path.exists(whitefile):
        return 0
    w = []
    for line in open(whitefile,'r'):
        if '.' in line:
            line.replace("\n","")
            w.append(line)
    return w

def gettestcase():
    try:
        return pickle.load(open(getlasttestcase(workpath+"result\\"), 'rb'))
    except Exception as e:
        return 0

def diffstr(str1,str2):
    return (difflib.SequenceMatcher(None, str(str1), str(str2))).quick_ratio() == 1.0

def setfilter(url,type):
    filter = []
    if whitelist:
        for line in whitelist:
            u, line = line.split(' ', 1)
            k, v = line.split('.',1)
            if (k == type and url ==u) or u=='*':
                filter.append(v.replace("\n", ""))
    return filter

def dictinsertdict(dicta,dictb):
    for k, v in dicta.items():
        x=dictb.get(k)
        if not isinstance(v,dict):
            dictb.update(dicta)
            return
        if x:
            dictinsertdict(v,x)
        else:
            dictb.update(dicta)

def finddiffindict2(url,dict1,key,value,path,type,info,finddiff,rule,newwhitelist):
    if isinstance(dict1,dict):
        for k, v in dict1.items():
            path.append(k)
            find=finddiffindict2(url,v,key,value,path,type,info,finddiff,rule,newwhitelist)
            if find:
                return find
            if not isinstance(v,dict):
                if k==key:
                    if rule and not diffstr(str(v),str(value)) :
                        strpath = '' + type
                        for p in path:
                            strpath = strpath + '.' + p
                        strpath = url +' '+ strpath
                        newwhitelist[strpath] = ''
                        diff={}
                        diff[k]=(value,v)
                        plast=path.pop()
                        for p in path[::-1]:
                            tmp=diff.copy()
                            diff={}
                            diff[p]=tmp
                        dictinsertdict(diff,info)
                        path.append(plast)
                    finddiff=1
                    return finddiff
            path.remove(k)
    return finddiff

def diffdict(url,dict1,dict2,path,type,info,rule,newwhitelist):
    filter = setfilter(url,type)
    if isinstance(dict1,dict):
        for k,v in dict1.items():
            path.append(k)
            filterpath = ''
            for p in path:
                filterpath = bool(filterpath =='') and (filterpath+ p)or(filterpath+ '.'+ p)
            if filterpath in filter or '*' in filter:
                path.remove(k)
                continue
            diffdict(url,v,dict2,path,type,info,rule,newwhitelist)
            if not isinstance(v,dict):
                find=0
                find=finddiffindict2(url,dict2,k,v,[],type,info,find,rule,newwhitelist)
                if not find:
                    diff = {}
                    if rule ==1 :
                        diff[k] = ('non-exist', v)
                        str=''+type
                        for p in path:
                            str=str+'.'+p
                        str=url+' '+str
                        newwhitelist[str] = ''
                    else:
                        diff[k] = (v, 'non-exist')
                        str = '' + type
                        for p in path:
                            str = str + '.' + p
                        str = url +' '+ str
                        newwhitelist[str] = ''
                    plast = path.pop()
                    for p in path[::-1]:
                        tmp = diff.copy()
                        diff = {}
                        diff[p] = tmp
                    info.update(diff)
                    path.append(plast)
            path.remove(k)

def check(id,url,params,code1,header1,body1,code2,header2,body2):
    global failnum
    diff={}
    tmp={}
    result={}
    result['api']=url+" "+params
    result['test differences']=diff
    url=(re.compile(r'://(.+)').findall(bool(url[-1]== '?') and url[0:-1] or url))[0]
    if diffstr(str(code1),str(code2)):
        tmp={}
        diffdict(url,header1, header2, [], 'header', tmp, 1, newwhitelist)
        diffdict(url,header2, header1, [], 'header', tmp, 0, newwhitelist)
        if tmp:
            diff['response headers'] = tmp
            tmp = {}
        diffdict(url,body1, body2, [], 'body', tmp, 1, newwhitelist)
        diffdict(url,body2, body1, [], 'body', tmp, 0, newwhitelist)
        if tmp:
            diff['response body'] = tmp
    else:
        diff['response code']=(code1,code2)
    if not diff:
        result['result']='PASS'
    else:
        result['result']='FAIL'
        failnum += 1
    testresults[id]=result

def send(url,method,payload,headers,**attrs):
    if method == 'POST':
        r = requests.post(url, data=payload, headers=headers,**attrs)
    if method == 'GET':
        r = requests.get(url, data=payload, headers=headers,**attrs)
    time.sleep(2)
    return (r.status_code,r.json(),r.headers)

def jsontodict(str):
    try:
        return json.load(str)
    except:
        return json.loads(re.compile(r'({.+})').findall(str)[0])

def strtodict(str,sp='&',op='='):
    dict={}
    try:
        list=str.split(sp)
    except ValueError:
        return dict
    for i in list:
        try:
            k,v=i.split(op)
            dict[k] = v
        except ValueError:
            break
    return dict

def testcasebuild(str):
    def replacesplit(str):
        return str.replace("\n", "").split(" ")[-1]
    global testnum
    testnum += 1
    (request, response) = str.split('Response ', 1)
    (_, rid, ishttps, rurl, _, requesquery, requestheader, requestbody) = request.split('Request ')
    (_, rop, ruid, rtime, raid) = rid.replace("\n", "").split(" ")
    (_, responsecode, reaponseheader, responsebody) = response.split('Response ')
    print(rtime)
    url = re.compile(r'url: (.+)').findall(rurl.split('?')[0])[0]
    params = replacesplit(requesquery)
    payload = ''
    if params != 'undefined':
        url = url + '?'
        payload=strtodict(urllib.parse.unquote(params))
    else:
        params = ''
    ishttps = replacesplit(ishttps)
    method=re.compile(r'header: (\w+)').findall(requestheader.split("\n")[0])[0]
    requestheader = strtodict(requestheader,'\n',': ')
    if 'header'in requestheader:
        del requestheader['header']
    responsecode = re.compile(r'code: (.+)').findall(responsecode.split("\n")[0])[0]
    reaponseheader = strtodict(reaponseheader,'\n',': ')
    if 'header' in reaponseheader:
        del reaponseheader['header']
    responsebody=re.compile(r'body: (.+)').findall(responsebody.split("\n")[0])[0]
    if payload == '' and requestbody != '':
        params=urllib.parse.unquote(re.compile(r'body: (.+)').findall(requestbody.split("\n")[0])[0])
        payload = strtodict(params)
    https=0
    if ishttps == 'True':
        https=1
        url = "https://" + url
    else:
        url = 'http://' + url
    print("url : " + url + ' ' + params + "    sending...")
    return url,method,payload,requestheader,rtime,params,https,responsecode,reaponseheader,responsebody

def process(str):
    url, method, payload, headers, rtime, params, https , code1, header1, body1 =testcasebuild(str)
    try:
        if https:
            (code2, body2, header2) = send(url, method, payload, headers,verify=False)
        else:
            (code2, body2, header2) = send(url, method, payload, headers)
    except Exception as e:
        print(e)
        (code2, body2, header2)=('send except!','{"errno":""}',{})
    header2=dict(header2)
    if not lasttestcase or rtime not in lasttestcase:
        body1 = jsontodict(body1)
        print("send done,checking self record...\n")
        check(rtime,url,params,code1,header1,body1,code2,header2,body2)
    else:
        print("send done,checking last test...\n")
        check(rtime, url, params, lasttestcase[rtime]['response code'], lasttestcase[rtime]['response header'], lasttestcase[rtime]['response body'], code2,header2,body2)
    testcase={}
    testcase["url"]=url
    if params=='':params=payload
    testcase["params"]=params
    testcase["response code"]=code2
    testcase["response header"] = dict(header2)
    testcase["response body"] = body2
    testcases[rtime]=testcase
    return (code2, body2, header2)

def fifoprocess(queue,n):
    while True:
        try:
            n-=1
            j=n
            str = queue.popleft()
            (code,body, header)=process(str)
            while(j>0):
                queue.append(middleware.rule(str,body,header,queue.popleft()))
                j-=1
            fifoprocess(queue,n)
        except IndexError:
            break

def run(dataflow):
    session = ''
    sessionid = ''
    pattern = re.compile(r'(\w+)')
    try:
        for i in open(recordfile, encoding='utf-16-le'):
            if not i.startswith("\n"):
                i = i.replace("\ufeff", "")
                session += i
            if i.startswith("Request id: "):
                id, sessionid = (int(pattern.findall(i)[4]),pattern.findall(i)[3])
            if i.startswith(sessionid + " end"):
                dataflow[id] = session
                session = ''
    except Exception as e:
        print("api record file open error, exit!")
        exit()
    if  os.path.exists(removefile):
        try:
            for i in open(removefile, encoding='utf-16-le'):
                if not i.startswith("\n"):
                    i = i.replace("\ufeff", "")
                    if i.startswith("Request id: "):
                        id= int(pattern.findall(i)[4])
                        if id in dataflow:
                            del dataflow[id]
        except Exception as e:
            print("api removefile file open error, exit test!")
            exit()
    dataflow = sorted(dataflow.items(), key=lambda x: x[0], reverse=False)
    n = 0
    for k, v in dataflow:
        Queue.append(v)
        n += 1
    fifoprocess(Queue, n)

def writelog(file,test,type='json'):
    try:
        if type=='json':
            return open(file, 'w').write(json.dumps(sorted(test.items(), key=lambda x: x[0], reverse=False), sort_keys=True, separators=(',', ':')))
        if type=='str':
            fileobj = open(file, 'w')
            for k, v in test.items():
                fileobj.write(k + '\n')
            fileobj.close()
        if type == 'listtostr':
            fileobj = open(file, 'w')
            for k, v in test:
                fileobj.write(k + '\n')
            fileobj.close()
        if type=='pickle':
            pickle.dump(test,open(file,'wb'))
    except Exception as e:
        pass

def report():
    global testnum, failnum,newwhitelist
    testresults[' In all'] = testnum
    testresults[' pass'] = testnum - failnum
    testresults[' fail'] = failnum
    curtime = getdate()
    print("test result:")
    n = 0
    for k, v in testresults.items():
        if k not in (' In all', ' pass', ' fail'):
            print(n)
            print(v)
            n += 1
    not whitelist and writelog(whitefile, newwhitelist, 'str')
    not os.path.exists(workpath + "result\\") and os.makedirs(workpath + "result\\")
    writelog(workpath + "result\\%sjson.log" % curtime, testcases)
    writelog(workpath + "result\\%sresult.log" % curtime, testresults)
    writelog(workpath + "result\\%sdiff.log" % curtime, newwhitelist, 'str')
    writelog(workpath + "result\\%s.txt" % curtime, testcases, 'pickle')
    print("\n%s tests , %s pass , %s fail " % (testnum, testnum - failnum, failnum))

if __name__ == "__main__":
    workpath="d:\\pythontest\\"
    if not os.path.exists(workpath):
        workpath = sys.path[0]+'\\'
    recordfile = workpath+"api\\record.gor"
    if not os.path.exists(recordfile):
        print("api record file not exist, exit test!")
        exit()
    removefile = workpath+"api\\remove.gor"
    whitefile = workpath+"config\\white.txt"
    testcase_dir = workpath+"result\\"
    whitelist = getwhitelist()
    lasttestcase = gettestcase()
    testresults = {}
    testcases = {}
    newwhitelist = {}
    Queue = deque()
    testnum = 0
    failnum = 0
    run({})
    report()


