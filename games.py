from ssl import SSLError
import requests
import click
import datetime as dt
import time
import pandas as pd
import requests
import csv
import math

def get_user_games(steam_id, key):
    req = requests.get(f'https://api.steampowered.com/IPlayerService/GetOwnedGames/v1/?key={key}&include_played_free_games=true&format=json&steamid={steam_id}')
    games = req.json()['response']['games']
    return games

def get_request(url, parameters=None):
    """Return json-formatted response of a get request using optional parameters.
    
    Parameters
    ----------
    url : string
    parameters : {'parameter': 'value'}
        parameters to pass as part of get request
    
    Returns
    -------
    json_data
        json-formatted response (dict-like)
    """
    try:
        response = requests.get(url=url, params=parameters)
    except SSLError as s:
        print('SSL Error:', s)
        
        for i in range(5, 0, -1):
            print('\rWaiting... ({})'.format(i), end='')
            time.sleep(1)
        print('\rRetrying.' + ' '*10)
        
        # recusively try again
        return get_request(url, parameters)
    
    if response:
        return response.json()
    else:
        # response is none usually means too many requests. Wait and try again 
        print('No response, waiting 10 seconds...')
        time.sleep(10)
        print('Retrying.')
        return get_request(url, parameters)

def parse_steamspy_request(appid):
    """Parser to handle SteamSpy API data."""
    url = "https://steamspy.com/api.php"
    parameters = {"request": "appdetails", "appid": appid}
    
    json_data = get_request(url, parameters)
    return json_data

def get_steamspy_data(id):
    steam_spy_data = parse_steamspy_request(id)
    positive, negative = steam_spy_data['positive'], steam_spy_data['negative']
    if negative == 0:
        if positive == 0:
            percentage = 0
        else:
            percentage = 100
    else:
        percentage = round(100 - (negative/(positive+negative)) * 100, 2)
        
    name = steam_spy_data['name']
    genre = steam_spy_data['genre']
    
    return percentage, name, genre

def get_user_games_info(steam_id, key):
    games_list = get_user_games(steam_id, key)
    
    games_info = []
    for i, game in enumerate(games_list):
        percentage = math.floor((i/len(games_list))*1000)
        if percentage % 100 == 0:
            print(f'{percentage/10}% of games info gotten.')
        
        playtime = game['playtime_forever']
        
        appid = game['appid']
        percentage, name, genre = get_steamspy_data(appid)
        
        games_info.append({'Game name': name, 'Review score': percentage, 'genre': genre, 'hours played':round(playtime/60,2)})
        headers = list(games_info[0].keys())
        
    with open(f'{steam_id}_games.csv', 'w', encoding="utf-8") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames = headers)
        writer.writeheader()
        writer.writerows(games_info)
            
def remove_and_sort(steam_id):
    df = pd.read_csv(f"{steam_id}_games.csv")
    df.drop(df[df['Review score'] == 0].index, inplace = True)
    df = df.sort_values(by='Review score', ascending=False)
    
    df.to_csv(f"{steam_id}_games_non_zero.csv")
    
def steam_64_id_getter(key, vanity_url):
    req = requests.get(f"http://api.steampowered.com/ISteamUser/ResolveVanityURL/v0001/?key={key}&vanityurl={vanity_url}")
    try:
        return req.json()['response']['steamid']
    except KeyError:
        print('Please enter a valid steam64 ID or vanity url.')

def get_user_id(key, text):
    if 'steamcommunity' in text:
        vanity_name = text.split('/')[-1]
        return steam_64_id_getter(key, vanity_name)
    elif text.isnumeric():
        return int(text)
    else:
        return steam_64_id_getter(key, text)
    
    
@click.command()
@click.option('-id', '--steam_ID', type=str, required=True, help='Your steam64 ID or vanity url.')
@click.option('-k', '--key', type=str, required=True, help='Your steam api key')
@click.option('-nz', '--non_zero', type=bool, default=False, help=f"y/n for if you would like a copy without reviews with 0% rating")
def click_main(steam_id, key, non_zero=False):
    user_id = get_user_id(key, steam_id)
    get_user_games_info(user_id, key)
    if non_zero:
        remove_and_sort(user_id)

if __name__ == '__main__':
    click_main()