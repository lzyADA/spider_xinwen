# -*- coding: utf-8 -*-

# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://doc.scrapy.org/en/latest/topics/item-pipeline.html


from pymongo import MongoClient

client = MongoClient(host='172.0.0.1', port=27017)

class Xinwen4Pipeline(object):
    def process_item(self, item, spider):
        if "content" in item:
            if len(item["content"]) > 150:
                collections = client["xinwen"]["toutiao"]
                ret_dict = collections.find_one({"docid": item["docid"]})
                if ret_dict == None:
                    collections.insert_one(item)

                else:
                    if item["commentCount"] != ret_dict["commentCount"]:
                        collections.update_one({"docid": item["docid"]},
                                               {"$set": {"commentCount": item["commentCount"]}})

