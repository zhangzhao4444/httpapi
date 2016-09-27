#!/usr/bin/evn python
# -*- coding:utf-8 -*-
import os
import requests
from collections import deque
import time
import urllib.parse
import middleware
import difflib
import pickle
import json
import datetime

def getlastfile():
    l = os.listdir(lastfile_dir)
    l.sort(key=lambda fn: os.path.getmtime(lastfile_dir + fn) if not os.path.isdir(lastfile_dir + fn) and os.path.splitext(lastfile_dir + fn)[1]=='txt' else 0)
    d=lastfile_dir+l[-1]
    return d

def getdate():
    return time.strftime("%Y-%m-%d-%H-%M-%S", time.localtime(time.time()))

def config():
    global havewhlist
    global whitelist
    global lastset
    global firstrun
    if not os.path.exists(whitefile):
        fileobj = open(whitefile, 'w')
        fileobj.close()
    fileobj = open(whitefile, 'r')
    for line in fileobj:
        if '.' in line:
            line.replace("\n", "")
            whitelist.append(line)
    if whitelist:
        havewhlist = 1
    fileobj.close()
    try:
        fileobj = open(getlastfile(), 'rb')
        lastset=pickle.load(fileobj)
        fileobj.close()
        if lastset:
            firstrun=0
    except Exception as e:
        pass

def list_dict(dict_a):
    if isinstance(dict_a,dict) :
        for k,v in dict_a.items():
            print("%s : %s" %(k,v))
            list_dict(v)

def diffstr(str1,str2):
    diff = difflib.SequenceMatcher(None,str(str1) ,str(str2))
    if diff.quick_ratio()!=1.0:
        return 0
    return 1

def diffdict(dict1,dict2,info,type):
    filter=[]
    for line in whitelist:
        k,v=line.split('.')
        if k==type:
            filter.append(v.replace("\n",""))
    for k, v in dict2.items():
        if k in filter:
            continue
        try:
            v2 = dict1[k]
            if not diffstr(str(v), str(v2)):
                info[k]=(v2,v)
                newwhitelist[type + '.' + k] = ''
        except Exception as e:
            info[k]=('non-existent',v)
            newwhitelist[type+'.'+k] =''
    for k, v in dict1.items():
        if k in filter:
            continue
        try:
            v2=dict2[k]
        except Exception as e:
            info[k] =(v2,'non-existent')
            newwhitelist[type + '.' + k] = ''

def checkself(time,url,params,recordcode,recordheader,recordbody,realcode,realbody,realheader):
    global passnum
    info={}
    testcase={}
    testcase['url']=url
    testcase['params']=params
    testcase['details']=info
    if diffstr(str(recordcode),str(realcode)):
        diffdict(recordheader, realheader,info,'header')
        diffdict(recordbody,realbody,info,'body')
    else:
        info['reopenscode']=(recordcode,realcode)
    if not info:
        testcase['result']='PASS'
        passnum+=1
    else:
        testcase['result']='FAIL'
    resultset[time]=testcase

def send(url,method,payload,headers):
    if method=='POST':
            r = requests.post(url,data=payload,headers=headers)
    if method=='GET':
            r = requests.get(url,data=payload,headers=headers)
    time.sleep(2)
    return (r.status_code,r.text,r.headers)

def process(str):
    global testnum
    testnum+=1
    (request,response)=str.split('Response ',1)
    (_,rid,ishttps,rurl, _, rquery, rheader,rbody)= request.split('Request ')
    (_,rop,ruid,rtime,raid)=rid.replace("\n","").split(" ")
    (_,recordcode, recordheader, recordbody) =response.split('Response ')
    url=rurl.split("?")[0].split(" ")[1].replace("\n","")
    params = rquery.replace("\n","").split(" ")[-1]
    payload=''
    if params !='undefined':
        url=url+'?'
        params=urllib.parse.unquote(params)
        payload = eval("{'" + params.replace("&", "','").replace("=", "':'") + "'}")
    else:
        params=''
    ishttps= ishttps.replace("\n","").split(" ")[-1]
    rbody= rbody.replace("\n","").split(" ")[-1]
    method= rheader.split("\n")[0].split(" ")[1]
    headers=eval("{'"+rheader.replace("\n", "','").replace(": ", "':'")[0:-2]+"}")
    del headers['header']
    recordcode= recordcode.replace("\n","").split(" ")[-1]
    recordheader=eval("{'"+recordheader.replace("\n", "','").replace(": ", "':'")[0:-2]+"}")
    del recordheader['header']
    recordbody=recordbody.replace("\n"," ").split(" ")[1]
    if payload==''and rbody!='':
        params=rbody
        params = urllib.parse.unquote(params)
        payload=eval("{'"+params.replace("&", "','").replace("=", "':'")+"'}")
    if ishttps=='True':
        url="https://"+url
    else:
        url='http://'+url
    print("url : "+url+' '+params +"    sending...")
    (realcode, realbody, realheader)=send(url, method, payload, headers)
    print("send done,checking...\n")
    if firstrun:
        checkself(rtime,url,params,recordcode,recordheader,eval(recordbody),realcode,eval(realbody),realheader)
    else:
        if rtime in lastset:
            checkself(rtime, url, params, lastset[rtime]['responsecode'], lastset[rtime]['responseheader'], lastset[rtime]['responsebody'], realcode, eval(realbody), realheader)
        else:
            info = {}
            info['id']=('non-existent',rtime)
            testcase = {}
            testcase['url'] = url
            testcase['params'] = params
            testcase['details'] = info
            testcase['result'] = 'FAIL'
            resultset[time] = testcase
    itemset={}
    itemset["url"]=url
    itemset["params"]=params
    itemset["responsecode"]=realcode
    itemset["responseheader"]=dict(realheader)
    itemset["responsebody"]=eval(realbody)
    runset[rtime]=itemset
    #print(runset[rtime])
    return (realcode, realbody, realheader)

def popprocess(deq,n):
    while True:
        try:
            n-=1
            j=n
            str = deq.popleft()
            (responsecode,responsebody, responseheader)=process(str)
            while(j>0):
                deq.append(middleware.rule(str,responsebody,responseheader,deq.popleft()))
                j-=1
            popprocess(deq,n)
        except IndexError:
            break

def createwl():
    if not havewhlist:
        fileobj = open(whitefile, 'w')
        for k, v in newwhitelist.items():
            fileobj.write(k + '\n')
        fileobj.close()

def run():
    global dataflow
    session = ''
    sessionid = ''
    try:
        data = open(recordfile, encoding='utf-16-le').readlines()
    except UnicodeEncodeError:
        data = open(recordfile, encoding='utf-8').readlines()
    for i in data:
        if not i.startswith("\n"):
            i = i.replace("\ufeff", "")
            session += i
            if i.startswith("Request id: "):
                timeid, sessionid = (int(i.split(" ")[4]), i.split(" ")[3])
            if i.startswith(sessionid + " end"):
                dataflow[timeid] = session
                session = ''
    if  os.path.exists(removefile):
        try:
            data = open(removefile, encoding='utf-16-le').readlines()
        except UnicodeEncodeError:
            data = open(removefile, encoding='utf-8').readlines()
        for i in data:
            if not i.startswith("\n"):
                i = i.replace("\ufeff", "")
                if i.startswith("Request id: "):
                    timeid, _ = (int(i.split(" ")[4]), i.split(" ")[3])
                    if timeid in dataflow:
                        del dataflow[timeid]
    dataflow = sorted(dataflow.items(), key=lambda x: x[0], reverse=False)
    n = 0
    for k, v in dataflow:
        deq.append(v)
        n += 1
    popprocess(deq, n)
    createwl()

def report():
    global testnum,passnum
    print("test result:")
    i=0
    for k, v in resultset.items():
        i+=1
        print(i)
        print(v)
    #json.dumps(resultset)
    pickle.dump(runset,open(lastfile,'wb'))
    #json.dumps(runset,open(lastjsonfile, 'w'))
    print("\n%s tests , %s pass , %s fail " %(testnum,passnum,testnum-passnum))


if __name__ == "__main__":
    recordfile = "D:\\pythontest\\api\\record.gor"
    removefile = "D:\\pythontest\\api\\remove.gor"
    whitefile = "D:\\pythontest\\config\\white.txt"
    curtime = getdate()
    lastfile = "D:\\pythontest\\result\\%s.txt" % curtime
    lastfile_dir = "D:\\pythontest\\result\\"
    lastjsonfile = "D:\\pythontest\\result\\%s.json" % curtime
    dataflow = {}
    deq = deque()
    firstrun = 1
    havewhlist = 0
    testnum=0
    passnum=0
    whitelist = []
    resultset = {}
    lastset={}
    runset={}
    newwhitelist = {}
    config()
    run()
    report()


