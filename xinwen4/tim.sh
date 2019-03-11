#! /bin/sh
. ~/.bash_profile
export PATH=$PATH:/usr/local/bin
cd /home/zhanghuaijie/shuju/jinritoutiao/yule/xinwen4
nohup scrapy crawl toutiao >> toutiao.log 2>&1 &

