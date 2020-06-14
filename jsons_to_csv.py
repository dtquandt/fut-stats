import pandas as pd
import os


path = './data/players/'

json_list = []

for filename in os.listdir(path):
    with open(path+filename, 'r', encoding='utf8') as f:
        json_str = f.read()
    json_list.append(json_str)

chained_jsons = '\n'.join(json_list)

final_df = pd.read_json(chained_jsons, lines=True)

final_df.to_csv('./data/player_data.csv', index=False)
