# httpapi
http api  记录回放，接口fuzz测试

A)自动抓包记录

利用fiddler插件c抓包，支持手工增加和删除，支持https

修改fiddlerjsconf.ini 抓取指定域名，抓取的包会记录到 record.gor提供给回放所用

修改fiddler.js中 OnBeforeResponse，DoAddSession 中包过滤规则
oSession.GetResponseBodyAsString().IndexOf("\"errno\":0") 

将fiddler\fiddler.js替换到fiddler4, Rules->Customize rules



B)回放测试：
python replay.py

1.白名单

config\white.txt

u.panda.tv/ajax_login body.errmsg

u.panda.tv/ajax_login body.errno

roll.panda.tv/get_comm body.data.ts

roll.panda.tv/get_comm header.*

\* header

校验屏蔽白名单中的项(支持区分api及通配符*)

首次运行程序根据第一次实际运行结果与record中的记录生成白名单，或删除白名单依据连续2次运行结果生成白名单，也可手动调整该名单

2.中间件
middleware.py

packet a-->send a-->a response-->middleware-->fix other packet-->send b

支持插件编程

用于动态参数 如token
