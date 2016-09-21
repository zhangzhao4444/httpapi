import urllib.parse
import re

def rule(recordstr, responsebody, responseheader, pendingstr):
    url = recordstr.split('Request ')[3].split("?")[0].split(" ")[1].replace("\n", "")
    if url=='www.3663.com/api/msg/send':
        body=eval(responsebody)
        token=urllib.parse.quote(body["data"])
        pendingstr, number = re.subn("content=(.*)&", "content="+token+"&", pendingstr)
    return pendingstr
