# -*- coding: utf-8 -*-
import scrapy
import hashlib
import execjs
import json
import re
import html
import datetime
import time
from copy import deepcopy
from fake_useragent import UserAgent
import threading



class ToutiaoSpider(scrapy.Spider):
    name = 'toutiao'
    allowed_domains = ['www.toutiao.com','www.nhc.gov.cn','p3.pstatp.com','p9.pstatp.com','p99.pstatp.com','p1.pstatp.com']
    start_urls = ['https://www.toutiao.com/']

    def __init__(self):
        ua = UserAgent(verify_ssl=False)
        user = ua.random
        global user
        self.headers = {'User-Agent': user,'Cookie': 'tt_webid=6618421848340776462','referer': 'https://www.toutiao.com/'}
        self.total_page = 1
        self.mutex = threading.Lock()
        super(ToutiaoSpider,self).__init__()


    def getsig(self,user,behot):
        # 获取_signature
        f1 = open('/home/zhanghuaijie/shuju/jinritoutiao/yule/xinwen4/xinwen4/tac.js', 'r')
        js = f1.read()
        ctx = execjs.compile(js)
        sig = ctx.call('a',user,behot)
        return sig



    def getHoney(self):
        # 获取as,cp
        t = int(time.time())  # 获取当前时间
        e = str('%X' % t)  # 十六进制数
        m1 = hashlib.md5()  # MD5加密
        m1.update(str(t).encode(encoding='utf-8'))  # 转化格式
        i = str(m1.hexdigest()).upper()  # 转化大写
        n = i[0:5]  # 获取前5位字符
        a = i[-5:]  # 获取后5位字符
        s = ''
        r = ''
        for x in range(0, 5):  # 交叉组合字符
            s += n[x] + e[x]
            r += e[x + 3] + a[x]

        AS = 'A1' + s + e[-3:]
        CP = e[0:3] + r + 'E1'
        return AS, CP

    def parse(self, response):
        item = {}
        item["name"] = "娱乐" # 频道分类
        behot = "0"
        AS,CP = self.getHoney()
        _signature = self.getsig(user,behot)

        url = 'https://www.toutiao.com/api/pc/feed/?category=news_entertainment' \
              '&utm_source=toutiao&widen=1&max_behot_time={}&max_behot_time_tmp={}&tadrequire=true' \
              '&as={}&cp={}&_signature={}'.format(behot,behot,AS,CP,_signature)

        yield scrapy.Request(url,callback=self.parse_list,meta={"item":deepcopy(item)},headers=self.headers)


    def parse_list(self, response):
        item = response.meta["item"]
        ret = response.text
        dict = json.loads(ret)
        behot_time = dict.get("next")
        if behot_time != None:
            behot = behot_time.get("max_behot_time")
            behot = str(behot)
            data = dict["data"]
            for da in data:
                item["docid"] = da.get("group_id")  # 新闻评论id
                item["title"] = da.get("title").strip()  # 新闻标题
                item["commentCount"] = da.get("comments_count")  # 跟帖量/评论数
                #新闻发布时间
                a = da.get("behot_time")
                T = time.localtime(a)
                item["ptime"] = time.strftime("%Y-%m-%d %H:%M:%S", T)  # 发布日期
                item["imgsrc"] = da.get("image_url")  # 列表页图片名
                item["source"] = da.get("source")  # 新闻媒体源
                url = da.get("source_url")
                if url.startswith('/'):
                    url = "https://www.toutiao.com/" + "a" + url.split('/')[-2]
                    item["url"] = url  # 新闻url
                    yield scrapy.Request(url,callback=self.parse_content,meta={"item":deepcopy(item)})

            # 翻页
            AS, CP = self.getHoney()
            _signature = self.getsig(user, behot)
            next_url = 'https://www.toutiao.com/api/pc/feed/?category=news_entertainment' \
                       '&utm_source=toutiao&widen=1&max_behot_time={}&max_behot_time_tmp={}&tadrequire=true' \
                       '&as={}&cp={}&_signature={}'.format(behot, behot, AS, CP, _signature)
            if self.total_page < 7:
                yield scrapy.Request(next_url, callback=self.parse_list, meta={"item": deepcopy(item)},headers=self.headers)
                self.mutex.acquire()
                self.total_page += 1
                self.mutex.release()


    def parse_content(self,response):
        # 获取新闻详情页内容
        item = response.meta["item"]
        ret = response.text
        try:
            item["content"] = re.findall(r'content: \'(.*?)\',',ret,re.S)[0]
            item["content"] = html.unescape(item["content"])
            regex = re.compile(r'data-content=\'\{\".+?\"\}\'|\<style\>.*?\</style\>|\<script\>.*?\</script\>|style=\".+?\"|classname=\".+?\"|target=\".+?\"|inline=\".+?\"|img_width=\".+?\"|img_height=\".+?\"|alt=\".+?\"|id=\".+?\"|\<script.*?\>.*?\</script\>|href=\".*?\"|class=\".+?\"|\'|\s+', re.S)
            item["content"] = regex.sub(' ', str(item["content"]))

            # src替换为图片名称/发送图片下载请求
            img_urls = re.findall(r'\"(http://.+?)\"', str(item['content']))
            if img_urls != []:
                for img_u in img_urls:
                    filename = "5" + "_" + item["docid"] + '_' + img_u.split('/')[-1]
                    item['content'] = re.sub(r'(%s)' % (img_u), filename, str(item['content']))
                    img_u = "https:" + img_u.split(":")[-1]
                    yield scrapy.Request(img_u, callback=self.parse_img, meta={"filename": filename},headers=self.headers)
        except:
            pass


        # 获取列表页图片url/下载
        img = item["imgsrc"]
        if img != None:
            filename = "5" + "_" + item["docid"] + '_' + img.split('/')[-1]
            item['imgsrc'] = re.sub(r'(%s)' % (img), filename, str(item['imgsrc']))
            img = "https:" + img
            yield scrapy.Request(img, callback=self.parse_list_img, meta={"filename": filename},headers=self.headers)


        # 当前爬取时间
        now = datetime.datetime.now()
        item["time"] = now.strftime("%Y-%m-%d %H:%M:%S")

        yield item

    def parse_img(self, response):
        # 保存图片
        filename = response.meta["filename"]
        imgs = "/data/crawler/toutiao/img/" + filename
        with open(imgs, 'wb') as f:
            f.write(response.body)

    def parse_list_img(self, response):
        # 保存图片
        filename = response.meta["filename"]
        imgs = "/data/crawler/toutiao/list_img/" + filename
        with open(imgs, 'wb') as f:
            f.write(response.body)



