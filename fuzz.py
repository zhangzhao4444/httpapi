#!/usr/bin/evn python
# -*- coding:utf-8 -*-
# @author: zhangzhao_lenovo@126.com
# @date: 20161018
# @version: 1.0.0.1003
import os
import sys
import requests
from collections import deque
import time
import urllib.parse
import middleware
import pickle
import json
import re
import random

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

def dictdelkey(dict,key):
    tmp=dict.copy()
    del tmp[key]
    return tmp

def dicttostr(dict,sp='&',op='='):
    str1=''
    for k,v in dict.items():
        str1= str1+k+op+str(v)+sp
    return str1[0:-1]

def dictmodify(dict,key,value):
    tmp = dict.copy()
    tmp[key]=value
    return tmp

def getdate():
    return time.strftime("%Y-%m-%d-%H-%M-%S", time.localtime(time.time()))

def send(url,method,payload,headers,**attrs):
    if method == 'POST':
        r = requests.post(url, data=payload, headers=headers,**attrs)
    if method == 'GET':
        r = requests.get(url, data=payload, headers=headers,**attrs)
    time.sleep(5)
    return (r.status_code,r.json(),r.headers)

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
    global apinum,testnum, failnum
    testresults[' APIs'] = apinum
    testresults[' In all'] = testnum
    testresults[' pass'] = testnum - failnum
    testresults[' fail'] = failnum
    curtime = getdate()
    print("\ntest result:")
    n = 0
    for k, v in testresults.items():
        if k not in (' In all', ' pass', ' fail',' APIs'):
            print(n)
            print(json.dumps(v))
            n += 1
    not os.path.exists(workpath + "result\\") and os.makedirs(workpath + "result\\")
    writelog(workpath + "result\\%sApiFuzzTest.log" % curtime, testresults)
    print("\n%s apis , %s tests , %s pass , %s fail " % (apinum , testnum, testnum - failnum, failnum))

def testcasebuild(str):
    def replacesplit(str):
        return str.replace("\n", "").split(" ")[-1]
    (request, response) = str.split('Response ', 1)
    (_, rid, ishttps, rurl, _, requesquery, requestheader, requestbody) = request.split('Request ')
    (_, rop, ruid, rtime, raid) = rid.replace("\n", "").split(" ")
    #print(raid)
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
    if payload == '' and requestbody != '':
        params=urllib.parse.unquote(re.compile(r'body: (.+)').findall(requestbody.split("\n")[0])[0])
        payload = strtodict(params)
    https=0
    if ishttps == 'True':
        https=1
        url = "https://" + url
    else:
        url = 'http://' + url
    return url,method,payload,requestheader,raid,params,https

def process(str):
    url, method, payload, headers, rtime, params, https = testcasebuild(str)
    try:
        if https:
            (code, body, header) = send(url, method, payload, headers, verify=False)
        else:
            (code, body, header) = send(url, method, payload, headers)
    except Exception as e:
        (code, body, header) = ('0', '', {})
    fuzzconstructor(url, method, payload, headers, rtime, params, https)
    return (code, body, header)

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
    global apinum
    session = ''
    sessionid = ''
    pattern = re.compile(r'(\w+)')
    try:
        for i in open(recordfile, encoding='utf-16-le'):
            if not i.startswith("\n"):
                i = i.replace("\ufeff", "")
                session += i
            if i.startswith("Request id: "):
                id, sessionid = (pattern.findall(i)[5],pattern.findall(i)[3])
            if i.startswith(sessionid + " end"):
                dataflow[id] = session
                session = ''
    except Exception as e:
        print(e)
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
    apinum = n
    fifoprocess(Queue, n)

def fuzztrigger(url, method, payload, headers, id, params, https,expectcode,case,fuzzresult):
    print("\n"+case)
    print("url : " + url + ' ' + params + "  sending...")
    global testnum,failnum
    testnum+=1
    result = {}
    code=0
    result['api'] = url + " " + params
    try:
        if https:
            (code, body, header) = send(url, method, payload, headers, verify=False)
        else:
            (code, body, header) = send(url, method, payload, headers)
        result['response code']=code
        result['response body']=body
        if code not in expectcode:
            result['result']='FAIL'
            failnum+=1
        else:
            result['result'] = 'PASS'
    except Exception as e:
        result['except']=str(e)
        result['result'] = 'FAIL'
        failnum+=1
    print(str(code))
    fuzzresult[case]=result

# fuzz test rule
# You can add custom fuzz testcase ,ep  XSS ==
########
def testcase1raw(url, method, payload, headers, id, params,https,expectcode, case, fuzzresult):
    fuzztrigger(url, method, payload, headers, id, params, https, expectcode, 'testcase1Raw', fuzzresult)

def testcase2noheader(url, method, payload, headers, id, params,https,expectcode, case, fuzzresult):
    fuzztrigger(url, method, payload, {}, id, params, https, expectcode, case, fuzzresult)

def testcase3nocookies(url, method, payload, headers, id, params,https,expectcode, case, fuzzresult):
    headers['Cookie']=''
    fuzztrigger(url, method, payload, headers, id, params, https, expectcode, case, fuzzresult)

def testcase4errorcookies(url, method, payload, headers, id, params,https,expectcode, case, fuzzresult):
    headers['Cookie']='__guid='
    fuzztrigger(url, method, payload, headers, id, params, https, expectcode, case, fuzzresult)

def testcase5noparams(url, method, payload, headers, id, params, https, expectcode, case, fuzzresult):
    fuzztrigger(url, method, {}, headers, id, '', https, expectcode, case, fuzzresult)

def testcase6lackparams(url, method, payload, headers, id, params,https,expectcode, case, fuzzresult):
    for k,v in payload.items():
        testcase = case + ' lack: ' + k + '=' + v
        fuzztrigger(url, method, dictdelkey(payload,k), headers, id, dicttostr(dictdelkey(strtodict(params),k)), https, expectcode, testcase, fuzzresult)

def testcase7moreparams(url, method, payload, headers, id, params,https,expectcode, case, fuzzresult):
    payload['test']='zz'
    params = params+ '&test=zz'
    fuzztrigger(url, method, payload, headers, id, params, https, expectcode, case, fuzzresult)

def testcase8blankvalue(url, method, payload, headers, id, params,https,expectcode, case, fuzzresult):
    for k,v in payload.items():
        testcase = case + ' ' + k + '= '
        fuzztrigger(url, method, dictmodify(payload, k, ' '), headers, id, dicttostr(dictmodify(strtodict(params), k, ' ')), https, expectcode, testcase, fuzzresult)

def testcase9nonevalue(url, method, payload, headers, id, params,https,expectcode, case, fuzzresult):
    for k,v in payload.items():
        testcase=case+' '+k+ '=None'
        fuzztrigger(url, method, dictmodify(payload, k, None), headers, id, dicttostr(dictmodify(strtodict(params), k, 'None')), https, expectcode, testcase, fuzzresult)

def testcase10nullvalue(url, method, payload, headers, id, params,https,expectcode, case, fuzzresult):
    for k, v in payload.items():
        testcase = case + ' ' + k + '=Null'
        fuzztrigger(url, method, dictmodify(payload, k, 'Null'), headers, id, dicttostr(dictmodify(strtodict(params), k, 'Null')), https, expectcode, testcase, fuzzresult)

def testcase11novalue(url, method, payload, headers, id, params,https,expectcode, case, fuzzresult):
    for k, v in payload.items():
        testcase = case + ' ' + k + '='
        fuzztrigger(url, method, dictmodify(payload, k, ''), headers, id, dicttostr(dictmodify(strtodict(params), k, '')), https, expectcode, testcase, fuzzresult)

def testcase12valueis0(url, method, payload, headers, id, params,https,expectcode, case, fuzzresult):
    for k, v in payload.items():
        testcase = case + ' ' + k + '=0'
        fuzztrigger(url, method, dictmodify(payload, k, 0), headers, id, dicttostr(dictmodify(strtodict(params), k, 0)), https, expectcode, testcase, fuzzresult)

def testcase13valueisf1(url, method, payload, headers, id, params,https,expectcode, case, fuzzresult):
    for k, v in payload.items():
        testcase = case + ' ' + k + '=-1'
        fuzztrigger(url, method, dictmodify(payload, k, -1), headers, id, dicttostr(dictmodify(strtodict(params), k, -1)),https, expectcode, testcase, fuzzresult)

def testcase14valueis0p0002(url, method, payload, headers, id, params,https,expectcode, case, fuzzresult):
    for k, v in payload.items():
        testcase = case + ' ' + k + '=0.00002'
        fuzztrigger(url, method, dictmodify(payload, k, 0.00002), headers, id, dicttostr(dictmodify(strtodict(params), k, 0.00002)), https, expectcode, testcase, fuzzresult)

def testcase15valueis2p0001(url, method, payload, headers, id, params,https,expectcode, case, fuzzresult):
    for k, v in payload.items():
        testcase = case + ' ' + k + '=2.00001'
        fuzztrigger(url, method, dictmodify(payload, k, 2.00001), headers, id, dicttostr(dictmodify(strtodict(params), k, 2.00001)), https, expectcode, testcase, fuzzresult)

def testcase16valuemaxint(url, method, payload, headers, id, params,https,expectcode, case, fuzzresult):
    for k, v in payload.items():
        testcase = case + ' ' + k + '=2147483648'
        fuzztrigger(url, method, dictmodify(payload, k, 2147483648), headers, id, dicttostr(dictmodify(strtodict(params), k, 2147483648)), https, expectcode, testcase, fuzzresult)

def testcase17valuemaxllong(url, method, payload, headers, id, params,https,expectcode, case, fuzzresult):
    for k, v in payload.items():
        testcase = case + ' ' + k + '=9223372036854775808'
        fuzztrigger(url, method, dictmodify(payload, k, 9223372036854775808), headers, id, dicttostr(dictmodify(strtodict(params), k, 9223372036854775808)), https, expectcode, testcase, fuzzresult)

def testcase18valueintmultin(url, method, payload, headers, id, params,https,expectcode, case, fuzzresult):
    for k, v in payload.items():
        n=random.randint(2,101)
        if isinstance(v, int):
            testcase = case + ' ' + k + '=' + v + '*'+ n
            fuzztrigger(url, method, dictmodify(payload, k, v*n), headers, id, dicttostr(dictmodify(strtodict(params), k, v+'*'+n)), https, expectcode, testcase, fuzzresult)
        else: continue

def testcase19valueintdivn(url, method, payload, headers, id, params,https,expectcode, case, fuzzresult):
    for k, v in payload.items():
        n=random.random()
        if isinstance(v, int):
            testcase = case + ' ' + k + '='+ v + '/'+ str(int(1/n))
            fuzztrigger(url, method, dictmodify(payload, k, v * n), headers, id, dicttostr(dictmodify(strtodict(params), k, v + '/' + str(int(1/n)))), https, expectcode, testcase, fuzzresult)
        else: continue

def testcase20valuestrshorten(url, method, payload, headers, id, params,https,expectcode, case, fuzzresult):
    for k, v in payload.items():
        if isinstance(v, str):
            v1= (len(v)<=3) and v or v[0:len(v)-1]
            testcase = case + ' ' + k + '=' + v1
            fuzztrigger(url, method, dictmodify(payload, k, v1), headers, id, dicttostr(dictmodify(strtodict(params), k, v1)), https, expectcode, testcase, fuzzresult)
        else: continue

def testcase21valuestrextend(url, method, payload, headers, id, params,https,expectcode, case, fuzzresult):
    for k, v in payload.items():
        v1 = ''
        if isinstance(v, str):
            for i in range(0,random.randint(2,9)) : v1 += v
            testcase = case + ' ' + k + '=' + v1
            fuzztrigger(url, method, dictmodify(payload, k, v1), headers, id, dicttostr(dictmodify(strtodict(params), k, v1)), https, expectcode, testcase, fuzzresult)
        else: continue

def testcase22valuestroverlen(url, method, payload, headers, id, params,https,expectcode, case, fuzzresult):
    for k, v in payload.items():
        v1=''
        if isinstance(v, str):
            n = 500
            #n=4294967294  max string ,..dot use!
            for i in range(0, n): v1 += '1'
            testcase = case + ' ' + k + '=' + v1
            fuzztrigger(url, method, dictmodify(payload, k, v1), headers, id, dicttostr(dictmodify(strtodict(params), k, v1)), https, expectcode, testcase, fuzzresult)
        else: continue

def testcase23valuestrillega(url, method, payload, headers, id, params,https,expectcode, case, fuzzresult):
    for k, v in payload.items():
        v1=',*&#%()='
        if isinstance(v, str):
            v1 = v + v1[random.randint(1,8) - 1] + v + v1[random.randint(1,8) - 1] + v
            testcase = case + ' ' + k + '='+ v1
            fuzztrigger(url, method, dictmodify(payload, k, v1), headers, id, dicttostr(dictmodify(strtodict(params), k, v1)), https, expectcode, testcase, fuzzresult)
        else: continue
#########

def fuzzconstructor(url, method, payload, headers, rtime, params, https):
    fuzz = {}
    expectcode = [200]
    fuzzresult={}
    print('------------\n'+'api : '+url+' '+params+'')
    fuzz['api'] = url + " " + params
    #testcases=['testcase2noheader','testcase3nocookies','testcase4errorcookies']
    testcases = ['testcase1raw','testcase5noparams','testcase6lackparams','testcase7moreparams',
                 'testcase8blankvalue','testcase9nonevalue','testcase10nullvalue','testcase11novalue','testcase12valueis0','testcase13valueisf1',
                 'testcase14valueis0p0002','testcase15valueis2p0001','testcase16valuemaxint','testcase17valuemaxllong','testcase18valueintmultin',
                 'testcase19valueintdivn','testcase20valuestrshorten','testcase21valuestrextend','testcase22valuestroverlen','testcase23valuestrillega']
    #testcases = ['testcase1raw','testcase23valuestrillega']
    for case in testcases:
        eval(case)(url, method, payload, headers, id, params,https,expectcode, case, fuzzresult)
    fuzz['fuzz result']=fuzzresult
    testresults[rtime]=fuzz

if __name__ == "__main__":
    workpath="d:\\pythontest\\"
    if not os.path.exists(workpath):
        workpath = sys.path[0]+'\\'
    recordfile = workpath+"api\\record.gor"
    if not os.path.exists(recordfile):
        print("api record file not exist, exit test!")
        exit()
    removefile = workpath+"api\\remove.gor"
    testresults = {}
    Queue = deque()
    testnum = 0
    failnum = 0
    apinum = 0
    run({})
    report()