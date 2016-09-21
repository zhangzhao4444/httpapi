#!/usr/bin/evn python
# -*- coding:utf-8 -*-
import os
import requests
from collections import deque
import time
import urllib.parse
import middleware

api_path = "D:\\pythontest\\api\\record.gor"

def process(str):
    (request,response)=str.split('Response ',1)
    (_,rid,ishttps,rurl, _, rquery, rheader,rbody)= request.split('Request ')
    (_,rop,ruid,rtime,raid)=rid.replace("\n","").split(" ")
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
    #print(rbody)
    if payload==''and rbody!='':
        params=rbody
        params = urllib.parse.unquote(params)
        payload=eval("{'"+params.replace("&", "','").replace("=", "':'")+"'}")
    if ishttps=='True':
        url="https://"+url
    else:
        url='http://'+url
    #print(url)
    #print(payload)
    #print(method)
    #print(headers)
    #print(rbody)
    if method=='POST':
            r = requests.post(url,data=payload,headers=headers)
    if method=='GET':
            r = requests.get(url,data=payload,headers=headers)
    #print(ruid)
    #print(r.status_code)
    #print(r.text)
    #print(r.headers)
    #print("\n")
    time.sleep(2)
    return (str,r.text,r.headers)

def middle(recordstr, responsebody, responseheader, pendingstr):
    middleware.rule(recordstr,responsebody, responseheader, pendingstr)
    return pendingstr

def popprocess(deq,n):
    while True:
        try:
            n-=1
            j=n
            str = deq.popleft()
            (recordstr,responsebody, responseheader)=process(str)
            while(j>0):
                pendingstr=deq.popleft()
                pendingstr=middle(recordstr,responsebody, responseheader, pendingstr)
                deq.append(pendingstr)
                j-=1
            popprocess(deq,n)
        except IndexError:
            break

try:
    data = open(api_path, encoding='utf-16-le').readlines()
except UnicodeEncodeError:
    data = open(api_path, encoding='utf-8').readlines()

sesson=''
dataflow={}
sessonid=''
deq=deque()

for i in data:
    if not i.startswith("\n"):
        i=i.replace("\ufeff","")
        sesson+=i
        if i.startswith("Request id: "):
            timeid,sessonid=(int(i.split(" ")[4]),i.split(" ")[3])
        if i.startswith(sessonid+" end"):
            dataflow[timeid]=sesson
            sesson=''
dataflow=sorted(dataflow.items(),key=lambda x:x[0],reverse=False)
n=0
for k,v in dataflow:
    deq.append(v)
    n+=1
#print(n)
popprocess(deq,n)


