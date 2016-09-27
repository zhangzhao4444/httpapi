# httpapi
http api  记录回放，接口fuzz测试

回放测试：
python replay.py

1.白名单

config\white.txt

header.Date

header.Transfer-Encoding

body.token

校验屏蔽白名单中的项

首次运行程序根据第一次实际运行结果与record中的记录生成白名单，或删除白名单依据连续2次运行结果生成白名单，也可手动调整该名单

2.中间件
middleware.py

packet a-->send a-->a response-->middleware-->fix other packet-->send b

支持插件编程

用于动态参数 如token
