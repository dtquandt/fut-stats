import scrapy
import json
import pandas as pd
import re
from bs4 import BeautifulSoup
from collections import OrderedDict
from datetime import datetime
import csv

cookies = {
    '__cfduid': 'de7ecf05c529770ae6e87e728d16781a31569629438',
    'platform': 'ps4',
    'xbox': 'true',
    'ps': 'true',
    'pc': 'true',
    'platform_type': 'console',
    'cookieconsent_status': 'dismiss',
    'theme_player': 'true',
    'PHPSESSID': '5be5475ffe8d0e1360dfbb638a8475eb',
    'comments': 'true',
    '__token': 'bacdc97e545395ff893f65fe7ade616799aed0daf5bf2dbd57397d21e768dfb04b87ad498839039eec971c5c47be953aa2d2fdc8c51654cceab3f2254d9e09d9',
    '__uname': 'Greedish',
}

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:72.0) Gecko/20100101 Firefox/72.0',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'en,en-US;q=0.7,pt-BR;q=0.3',
    'Referer': 'https://www.futbin.com/',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1',
    'DNT': '1',
    'Cache-Control': 'max-age=0',
    'TE': 'Trailers',
}

class FutSpider(scrapy.Spider):
    
    custom_settings = {
        'LOG_LEVEL': 'INFO'
    }

    name = 'futbin_spider'
    allowed_domains = ['www.futbin.com']
    
    def start_requests(self):
        df = pd.read_csv('C:\\Repos\\Futbin\\futbin_urls.csv', encoding='utf8')
        df['id'] = df['player-href'].apply(lambda x: re.search(r'player\/(\d+)\/', x).group(1))
        urls = df['player-href']
        for url in urls:
            yield scrapy.Request(url = url, callback = self.parse, meta = {'name': df[df['player-href'] == url]['player'].iloc[0], 'id': df[df['player-href'] == url]['id'].iloc[0]}, headers=headers, cookies=cookies)

    def parse(self, response):

        player_info = OrderedDict()
        player_info['futbin_url'] = response.request.url
        player_info['short_name'] = response.request.meta['name']
        player_info['futbin_id'] = response.request.meta['id']
        
        soup = BeautifulSoup(response.text, 'lxml')
        
        player_info['position'] = soup.select('div.pcdisplay-pos')[0].text
        player_info['rating'] = soup.select('div.pcdisplay-rat')[0].text
        
        player_card = soup.select('div#Player-card')[0]
        player_info['rarity'] = player_card['data-level']
        player_info['is_rare'] = player_card['data-rare-type']
            
        player_stats = json.loads(soup.select('#player_stats_json')[1].text.strip())
        
        for stat in player_stats.keys():
            if stat != 'test':
                if stat in ['ppace', 'pshooting', 'ppassing', 'pdribbling', 'pdefending', 'pphysical']:
                    player_info['{}_{}'.format('attr', stat)] = player_stats[stat]    
                else:
                    player_info['{}_{}'.format('stat', stat)] = player_stats[stat]
                    
        info_table = soup.select('table.table-info > tr')
        
        for item in info_table:
            field = item.find('th').text.strip()
            value = item.find('td').text.strip()
            if field == 'R.Face':
                value = item.select('td > i')[0]['class'][0]
            if field == 'Age':
                dob = ''.join(item.select('td > a')[0]['title']).replace('DOB - ', '')
                if not dob:
                    dob = ''.join(item.select('td > a')[0]['data-original-title']).replace('DOB - ', '')
                day, month, year = dob.split('-')
                player_info['birthdate'] = '-'.join([year,month,day])
                value = value.replace('years old', '').strip()
            if field == 'DOB':
                field = 'birthdate'
                day, month, year = value.strip().split('-')
                value = '-'.join([year, month, day])
            if field and value:
                player_info[field] = value
        
        for platform in ['ps4', 'xbox', 'pc']:
            player_info[platform+'_pgp_red_cards'] = soup.select('div.'+platform+'-pgp-data')[1].text.strip()
            player_info[platform+'_pgp_yellow_cards'] = soup.select('div.'+platform+'-pgp-data')[2].text.strip()
            player_info[platform+'_pgp_assists'] = soup.select('div.'+platform+'-pgp-data')[3].text.strip()
            player_info[platform+'_pgp_goals'] = soup.select('div.'+platform+'-pgp-data')[4].text.strip()
            player_info[platform+'_pgp_games'] = soup.select('div.'+platform+'-pgp-data')[5].text.strip()
        
        player_info['img_face'] = soup.select('img#player_pic')[0]['src']
        player_info['img_country'] = soup.select('img#player_nation')[0]['src']
        player_info['img_club'] = soup.select('img#player_club')[0]['src']
        
        player_info['upvotes'] = soup.select('span#votes_up')[0].text
        player_info['downvotes'] = soup.select('span#votes_down')[0].text
        
        traits = soup.select('div.its_tr')
        trait_list = []
        
        for item in traits:
            trait_list.append(item.text.strip())
        
        player_info['traits'] = ','.join(sorted(trait_list))
        
        yield player_info
        

class PriceSpider(scrapy.Spider):
            
        name = 'price_spider'
        allowed_domains = ['www.futbin.com']
        
        custom_settings={
            'ITEM_PIPELINES' : {'futbin_spider.pipelines.NoPipeline': 300},
            'LOG_LEVEL': 'INFO',
        }
        
        def start_requests(self):
            self.fieldnames = ['player_id', 'platform', 'date', 'price']
            self.csv_file = open('C:/Repos/Futbin/player_prices.csv', 'w', encoding='utf8', newline='')
            self.writer = csv.DictWriter(self.csv_file, fieldnames=self.fieldnames)
            self.writer.writeheader()
            df = pd.read_csv('C:/Repos/Futbin/player_info.csv')
            #df = df[df['rating'] > 75]
            df['photo_id'] = df['img_face'].apply(lambda x: re.search(r'(\d+)\.png', x).group(1) if re.search(r'(\d+)\.png', x) else None)
            for photo_id in df['photo_id']:
                if not photo_id:
                    continue 
                url = 'https://www.futbin.com/20/playerGraph?type=daily_graph&year=20&player={}&set_id='.format(str(photo_id))
                yield scrapy.Request(url = url, meta = {'id': str(photo_id)})
                
        def parse(self, response):
            
            prices = json.loads(response.text)
            player_id = response.request.meta['id']
            price_list = []
            
            for key in prices:
                for pair in prices[key]:
                    entry = {}
                    timestamp = pair[0]
                    entry['player_id'] = player_id
                    entry['date'] = datetime.fromtimestamp(int(timestamp)/1000).strftime('%Y-%m-%d')
                    entry['platform'] = key
                    entry['price'] = pair[1]
                    price_list.append(entry)
                    
            self.writer.writerows(price_list)
            
            yield None
                    
                    