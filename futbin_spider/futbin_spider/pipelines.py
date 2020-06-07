# -*- coding: utf-8 -*-

# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://docs.scrapy.org/en/latest/topics/item-pipeline.html

import csv
import logging
import pandas as pd

class CsvWriterPipeline(object):

    def open_spider(self, spider):
        self.file_path = 'C:\\Repos\\Futbin\\player_info.csv'
        self.items = []
        self.colnames = []
        self.count = 0

    def close_spider(self, spider):
        self.file = open(self.file_path, 'w', newline='', encoding='utf8')
        csvWriter = csv.DictWriter(self.file, fieldnames = self.colnames)
        logging.info("HEADER: " + str(self.colnames))
        csvWriter.writeheader()
        for item in self.items:
            csvWriter.writerow(item)
        self.file.close()

    def process_item(self, item, spider):
        self.count += 1
        for key in item.keys():
            if key not in self.colnames:
                self.colnames.append(key)
        self.items.append(item)
        if self.count % 100 == 0:
            self.count = 0
            self.close_spider(spider)
        return item
    
class DfPipeline(object):
    
    def open_spider(self, spider):
        self.df = ''
        self.count = 0
    
    def process_item(self, item, spider):
        self.count += 1
        if type(self.df) == str:
            self.df = pd.DataFrame(item['item'])
        else:
            self.df = pd.concat([self.df, pd.DataFrame(item['item'])], ignore_index=True)
        if self.count % 100 == 0:
            self.close_spider(spider)
            
    def close_spider(self, spider):
        print('{} items processed. Writing to file.'.format(self.count))
        self.df.to_csv('C:\\Repos\\Futbin\\player_prices.csv')
        
class NoPipeline(object):
    
    def open_spider(self, spider):
        self.count = 0
        pass
    
    def process_item(self, item, spider):
        self.count += 1
        if self.count % 100 == 0:
            print('{} items processed so far.'.format(self.count))
            
    def close_spider(self, spider):
        pass