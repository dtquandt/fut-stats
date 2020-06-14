import scrapy
import json
import pandas as pd
import re
import os
from bs4 import BeautifulSoup
from collections import OrderedDict
from datetime import datetime
import csv

cookies = {
    '__cfduid': 'd204b0c7754137ca1d1dacfbffa3031cc1592096418',
    'PHPSESSID': '87e0a9dc8558e9eb04b6d99cedc6261b',
    'theme_player': 'true',
    'comments': 'true',
    'platform': 'ps4',
}

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:77.0) Gecko/20100101 Firefox/77.0',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'en,en-US;q=0.7,pt-BR;q=0.3',
    'DNT': '1',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1',
    'Cache-Control': 'max-age=0',
    'TE': 'Trailers',
}

class FutSpider(scrapy.Spider):
    
    custom_settings = {
        'LOG_LEVEL': 'INFO',
        'ITEM_PIPELINES' : {'futbin_spider.pipelines.NoPipeline': 300},
    }

    name = 'futbin_spider'
    allowed_domains = ['www.futbin.com']
    
    def start_requests(self):
        
        player_urls = pd.read_csv('../data/player_urls.csv', encoding='utf8')
        player_cache = [filename.replace('.json', '') for filename in os.listdir('../data/players/')]
        player_urls['id'] = player_urls['url'].apply(lambda x: re.search(r'player\/(\d+)\/', x).group(1))
        new_player_urls = player_urls[~player_urls['id'].isin(player_cache)].copy()
        urls = new_player_urls['url']
        for url in urls:
            yield scrapy.Request(url = url, callback = self.parse, headers=headers, cookies=cookies)

    def parse(self, response):

        player_info = OrderedDict()
        player_info['futbin_url'] = response.request.url
        player_info['url_id'] = re.search(r'player\/(\d+)\/', response.request.url).group(1)
        
        soup = BeautifulSoup(response.text, 'lxml')
        
        face_url = soup.select('img#player_pic')[0]['src']
        player_info['futbin_id'] = re.search(r'(\d+)\.png', face_url).group(1)
        
        player_info['short_name'] = soup.select('li.breadcrumb-item.active')[0].text
        
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
        
        player_info['img_face'] = face_url
        player_info['img_country'] = soup.select('img#player_nation')[0]['src']
        player_info['img_club'] = soup.select('img#player_club')[0]['src']
        
        player_info['upvotes'] = soup.select('span#votes_up')[0].text
        player_info['downvotes'] = soup.select('span#votes_down')[0].text
        
        traits = soup.select('div.its_tr')
        trait_list = []
        
        for item in traits:
            trait_list.append(item.text.strip())
        
        player_info['traits'] = ','.join(sorted(trait_list))
        
        real_stats = soup.select('div.row.player-rs-holder')
        if real_stats:
            real_stats = real_stats[0]
            real_vals = real_stats.select('div.rs-stat-val')
            player_info['real_matches'] = real_vals[0].text
            player_info['real_goals'] = real_vals[1].text
            player_info['real_assists'] = real_vals[2].text
            player_info['real_own_goals'] = real_vals[3].text
            player_info['real_yellow_cards'] = real_vals[4].text
            player_info['real_red_cards'] = real_vals[5].text
            player_info['real_sub_in'] = real_vals[6].text
            player_info['real_sub_out'] = real_vals[7].text
        
        
        
        
        player_json = json.dumps(player_info, ensure_ascii=False)
        
        with open(f"../data/players/{player_info['url_id']}.json", 'w', encoding='utf8') as f:
            f.write(player_json)
            
        yield player_info
        

class PriceSpider(scrapy.Spider):
            
        name = 'price_spider'
        allowed_domains = ['www.futbin.com']
        
        custom_settings={
            'ITEM_PIPELINES' : {'futbin_spider.pipelines.NoPipeline': 300},
            'LOG_LEVEL': 'INFO',
        }
        
        def start_requests(self):
            
            min_rating = 0
            csv_path = '../data/price_data.csv'
            player_data_path = '../data/player_data.csv'
            
            self.fieldnames = ['futbin_id', 'platform', 'date', 'price']
            self.csv_file = open(csv_path, 'w', encoding='utf8', newline='')
            self.writer = csv.DictWriter(self.csv_file, fieldnames=self.fieldnames)
            self.writer.writeheader()
            
            player_data = pd.read_csv(player_data_path)
            player_data = player_data[player_data['rating'] > min_rating]
            
            for futbin_id in player_data['futbin_id']:
                url = f'https://www.futbin.com/20/playerGraph?type=daily_graph&year=20&player={futbin_id}&set_id='
                yield scrapy.Request(url = url, meta = {'id': str(futbin_id)})
                
        def parse(self, response):
            
            prices = json.loads(response.text)
            futbin_id = response.request.meta['id']
            price_list = []
            
            for key in prices:
                for pair in prices[key]:
                    entry = {}
                    timestamp = pair[0]
                    entry['futbin_id'] = futbin_id
                    entry['date'] = datetime.fromtimestamp(int(timestamp)/1000).strftime('%Y-%m-%d')
                    entry['platform'] = key
                    entry['price'] = pair[1]
                    price_list.append(entry)
                    
            self.writer.writerows(price_list)
            
            yield None
                    

class PlayerUrlSpider(scrapy.Spider):
    
    num_pages = 754
    name = 'player_url_spider'
    custom_settings={
            'LOG_LEVEL': 'INFO',
    }
    allowed_domains = ['futbin.com']
    
    start_urls=[f'https://futbin.com/players/?page={page_num}' for page_num in range(1, num_pages+1)]
    
    def parse (self, response):
        
        base_url = 'https://www.futbin.com'
        soup = BeautifulSoup(response.text, 'lxml')
        players = soup.find_all('a', class_='player_name_players_table')
        for player in players:
            result = {'player': player.text, 'url':base_url+player['href']}
            yield result