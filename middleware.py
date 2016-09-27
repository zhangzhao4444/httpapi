import urllib.parse
import re

def rule(str,body,header,pstr):
    """
    url=str.split('Request ')[3].split("?")[0].split(" ")[1].replace("\n","")
    if url=='www.3663.com/api/msg/send':
        body=eval(body)
        token=urllib.parse.quote(body["data"])
        pstr,_=re.subn("content=(.*)&","content="+token+"&",pstr)
    """
    return pstr
