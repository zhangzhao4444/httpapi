# httpapi(python3)
http api  记录回放，接口fuzz测试

### A)自动抓包记录

利用fiddler js插件开发完成自动抓包，支持手工增加和删除，支持https

修改fiddlerjsconf.ini 指定域名，抓取的包会记录到 record.gor提供给回放所用

修改fiddler.js中 OnBeforeResponse，DoAddSession 包过滤规则
oSession.GetResponseBodyAsString().IndexOf("\"errno\":0") 

将fiddler\fiddler.js替换到fiddler4, Rules->Customize rules，运行待测程序自动抓取数据包

手动增删：在fiddler某条记录右键选1add 或2delete

### B)回放测试：
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

用于解决动态参数 如token

3.测试结果

尚未完成独立报告模块，仅将运行结果打印

运行测试后result目录下会生成 :

xxxdiff.log 本次测试与上次测试response差异

xxxjson.log 本次测试返回的response json

xxxresult.log 测试结果结构化显示差异，可在json.cn 中显示更直观

### C api wiki抓取

python check.py

从wiki中拉取api，计算record中api覆盖率

提供三种拉取方法，如cookies（自己先登陆并抓包手动获取cookies，覆盖代码中的cookiesstr），seleium（修改登陆标记），pem（获取location重定项，待证书发送https登陆，带回cookies）

wiki中获取api需结合自身修改正则

### D api fuzz test(未完成)
