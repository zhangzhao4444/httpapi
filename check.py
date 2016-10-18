#!/usr/bin/evn python
# -*- coding:utf-8 -*-
# @author: zhangzhao_lenovo@126.com
# @date: 20161012
# @version: 1.0.0.1005
import os
import sys
import requests
import re
import hashlib
from bs4 import BeautifulSoup

def md5(s):
    s=s.lower()
    m=hashlib.md5()
    m.update(s.encode(encoding="utf-8"))
    return m.hexdigest()

def dictkey2str(str,sp='&',op='='):
    string=''
    try:
        list = str.split(sp)
    except ValueError:
        return string
    for i in list:
        try:
            k, v = i.split(op,1)
            string=string+k
        except ValueError:
            break
    return string

def getrecordapi(str,api):
    (request, _) = str.split('Response ', 1)
    (_, rid, _, rurl, _, requesquery, _, requestbody) = request.split('Request ')
    (_, rop, ruid, _, _) = rid.replace("\n", "").split(" ")
    url = re.compile(r'url: (.+)').findall(rurl.split('?')[0])[0]
    #params =requesquery.replace("\n", "").split(" ")[-1]
    #if params == '' and requestbody != '':
        #params=urllib.parse.unquote(re.compile(r'body: (.+)').findall(requestbody.split("\n")[0])[0])
    #urlparmas=url+'?'+dictkey2str(params)
    #api[md5(urlparmas)]=urlparmas
    api[md5(url)] = url

def funcert(url):
    # must be rewritten :payload,pem
    session = requests.Session()
    r = session.get(url, allow_redirects=False)
    location=r.headers['Location']
    url,ref=location.split('?',1)
    payload={}
    payload['user']='xxx'
    payload['passwd']='xxx'
    payload['ref'] = ref
    r = session.post(url,data=payload,verify=False)
    #pem='xx.pem'
    #r = session.get(url,data=payload,verify=pem)
    return r.text

def funcookies(url):
    # must be rewritten :cookie invalid
    cookiesstr = 'Cookie: confluence-sidebar.width=285;JSESSIONID=xx'
    k, v = cookiesstr.split(':', 1)
    cookies = {}
    cookies[k]=v
    session = requests.Session()
    r = session.get(url, cookies=cookies, verify=False)
    return r.text
    #.encode('gbk', 'ignore')

def funselenium(url):
    # must be rewritten : find_element_by_id xxx,send_keys xxx
    from selenium import webdriver
    from selenium.webdriver.support.wait import WebDriverWait
    from selenium.webdriver.support import expected_conditions as ec
    from selenium.webdriver.common.by import By
    try:
        browser=webdriver.Chrome()
        browser.get(url)
        elem = browser.find_element_by_id("user")
        elem.send_keys("xx")
        elem = browser.find_element_by_id("passwd")
        elem.send_keys("xx")
        elem = browser.find_element_by_id("loginButton")
        elem.click()
        WebDriverWait(browser, 200, 0.5).until(ec.presence_of_element_located((By.ID, 'logout-link') ))
        elem = browser.find_element_by_xpath('/html/body')
        return browser.page_source
    finally:
        browser.quit()

def getwikiapi(url,api):
    # This fun must be rewritten ,ep class=message-content, ep regular=3663.com/api.*
    # can be use cookies or pem or selenium
    body=funcookies(url)
    #body=funselenium(url)
    soup = BeautifulSoup(body ,"html.parser")
    print(soup.title)
    for p in soup.select(".message-content > p"):
        # if p. not in re.compile(r'abandoned'). ; filter abandoned api
        for str in p.find_all(string=re.compile('3663.com/api.*')):
            url=(re.compile(r'http://(.+)').findall(str)[0]).replace('demo','www').split('?',1)[0]
            api[md5(url)] = url

def report(tapi,rapi):
    total=1
    lack=1
    error={}
    total=len(tapi)
    for id,url in rapi.items():
        if id in tapi:
            del tapi[id]
        else:
            error[id]=url
    lack = len(tapi)
    print('\nrecord.gor cover :')
    for k,v in rapi.items():
        print(v)
    print('\nnot cover :')
    for k,v in tapi.items():
        print(v)
    print('\nerror! not in wiki :')
    for k,v in error.items():
        print(v)
    print("\napi in wiki : %s , record.gor cover : %s  , no cover : %s  , coverage %.2f" % (total, total-lack, lack, (total-lack)/total *100))
    print('\nplease check')

def run(dataflow,wikis):
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
    except Exception:
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
        except Exception:
            print("api removefile file open error, exit test!")
            exit()
    dataflow = sorted(dataflow.items(), key=lambda x: x[0], reverse=False)
    recordapi={}
    for k, v in dataflow:
        getrecordapi(v,recordapi)
    #print(set(recordapi))
    api={}
    try:
        for url in wikis:
            getwikiapi(url, api)
    except Exception:
        print("wiki open failed")
    if not api: print("wiki api parser failed !,exit")
    else: report(api,recordapi)

if __name__ == "__main__":
    workpath="d:\\pythontest\\"
    if not os.path.exists(workpath):
        workpath = sys.path[0]+'\\'
    recordfile = workpath+"api\\record.gor"
    if not os.path.exists(recordfile):
        print("api record file not exist, exit test!")
        exit()
    removefile = workpath+"api\\remove.gor"
    wikis = ['http://xxx/pages/viewpage.action?pageId=4426709']
    run({},wikis)